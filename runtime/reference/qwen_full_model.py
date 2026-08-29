"""Independent complete Qwen target-precision execution reference.

This checker reads the locked checkpoint directly.  It imports neither the
HBM/SRAM physical compiler, its checker, nor the artifact-driven simulator.
Matrix weights remain in checkpoint row-major layout and execute as explicit
256-element K segments; vector, attention, selection, and state operations use
the independent scalar architectural references.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from compiler.frontend.checkpoint import (
    CheckpointError,
    LockedCheckpointReader,
    load_checkpoint_lock,
)
from compiler.tensor_accelerator.common import (
    ArtifactError,
    align_up,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_sha256,
    sha256_bytes,
)
from compiler.tensor_accelerator.production_capability import (
    ProductionCapabilityError,
    load_production_capability,
)
from compiler.tensor_accelerator.production_model import (
    ProductionModelGraphError,
    ProductionOperation,
    load_production_model_graph,
)

from .tensor_accelerator_attention import (
    AttentionReferenceError,
    KVSnapshotReference,
    PreparedKVReference,
    commit_kv_group,
    empty_kv_snapshot,
    gqa_causal_attention_bf16,
    prepare_kv_append,
)
from .tensor_accelerator_bf16 import (
    BF16MatrixReferenceError,
    dense_bf16_linear_selected_rows_bf16,
)
from .tensor_accelerator_elementwise import (
    ElementwiseReferenceError,
    bf16_add_rne,
    qwen3_silu_mul_bf16,
)
from .tensor_accelerator_rmsnorm import (
    EPSILON_CODE,
    RMSNormReferenceError,
    rms_norm_bf16,
)
from .tensor_accelerator_rope import RoPEReferenceError, rope_bf16
from .tensor_accelerator_selection import (
    SelectionReferenceError,
    last_token_select_bf16,
)


REFERENCE_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_reference.v1"
EXECUTION_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_execution.v1"
REQUEST_SCHEMA = "opentallas.tensor_accelerator.qwen_full_model_request.v1"
REFERENCE_VERSION = "tensor-accelerator-qwen-full-model-reference-0.1.0"
SIMULATOR_VERSION = "tensor-accelerator-qwen-full-model-simulator-0.1.0"

MODEL_ID = "qwen3-8b"
OPERATION_COUNT = 617
TENSOR_COUNT = 1053
WEIGHT_COUNT = 399
STATE_COUNT = 36
LAYER_COUNT = 36
CONTEXT_CAPACITY = 8000
HIDDEN_WIDTH = 4096
INTERMEDIATE_WIDTH = 12288
VOCABULARY_SIZE = 151936
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
N_TILE = 64
K_TILE = 256
BF16_BYTES = 2
STATE_METADATA_BYTES = 64


class QwenFullModelReferenceError(ArtifactError):
    """Raised at the first independent complete-model divergence."""


def _canonical(path: Path, label: str) -> dict[str, Any]:
    value = load_strict_json(path)
    if path.read_bytes() != canonical_json_bytes(value):
        raise QwenFullModelReferenceError(f"{label} is not canonical JSON")
    return value


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise QwenFullModelReferenceError(f"{label} identity differs")


def _exact(
    value: Mapping[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    try:
        exact_keys(dict(value), required, optional, label)
    except ArtifactError as exc:
        raise QwenFullModelReferenceError(str(exc)) from exc


def _payload(values: object) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _u32_payload(values: object) -> bytes:
    return np.ascontiguousarray(values, dtype="<u4").tobytes(order="C")


def _capture(values: np.ndarray[Any, Any]) -> dict[str, Any]:
    payload = _payload(values)
    return {
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _codes(payload: bytes, shape: tuple[int, ...], label: str) -> np.ndarray[Any, Any]:
    elements = int(np.prod(shape, dtype=np.int64))
    if len(payload) != elements * BF16_BYTES:
        raise QwenFullModelReferenceError(f"{label} byte count differs")
    values = np.frombuffer(payload, dtype="<u2").reshape(shape)
    if np.any((values & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise QwenFullModelReferenceError(f"{label} contains BF16 NaN or infinity")
    return np.ascontiguousarray(values, dtype=np.uint16)


def _read_slice(
    reader: LockedCheckpointReader,
    tensor_name: str,
    *,
    start: int,
    size: int,
) -> tuple[bytes, dict[str, Any]]:
    record = reader.tensor_record(tensor_name)
    if start < 0 or size < 1 or start + size > record["size_bytes"]:
        raise QwenFullModelReferenceError(
            f"checkpoint slice for {tensor_name!r} is out of range"
        )
    result = bytearray(size)
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        chunk_end = cursor + len(chunk)
        overlap_start = max(start, cursor)
        overlap_end = min(start + size, chunk_end)
        if overlap_start < overlap_end:
            result[overlap_start - start : overlap_end - start] = chunk[
                overlap_start - cursor : overlap_end - cursor
            ]
        cursor = chunk_end

    reader.consume_tensor_payload(tensor_name, consume)
    if cursor != record["size_bytes"]:
        raise QwenFullModelReferenceError(
            f"checkpoint traversal for {tensor_name!r} differs"
        )
    return bytes(result), record


def _read_tensor(
    reader: LockedCheckpointReader,
    tensor_name: str,
) -> tuple[bytes, dict[str, Any]]:
    record = reader.tensor_record(tensor_name)
    if record["size_bytes"] > 4 * 1024 * 1024:
        raise QwenFullModelReferenceError(
            f"direct materialization of large tensor {tensor_name!r} is forbidden"
        )
    return _read_slice(reader, tensor_name, start=0, size=record["size_bytes"])


def _decode(values: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
    bits = np.ascontiguousarray(values, dtype=np.uint16).astype(np.uint32)
    return (bits << np.uint32(16)).view(np.float32)


def _encode(values: np.ndarray[Any, Any]) -> tuple[np.ndarray[Any, Any], int]:
    finite = np.ascontiguousarray(values, dtype=np.float32)
    if not np.all(np.isfinite(finite)):
        raise QwenFullModelReferenceError(
            "independent matrix arithmetic produced NaN or infinity"
        )
    bits = finite.view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    rounded = upper + increment.astype(np.uint32)
    saturated = (rounded & np.uint32(0x7F80)) == np.uint32(0x7F80)
    saturation = int(np.count_nonzero(saturated))
    rounded = np.where(
        saturated,
        (rounded & np.uint32(0x8000)) | np.uint32(0x7F7F),
        rounded,
    )
    rounded = np.where((rounded & np.uint32(0x7FFF)) == 0, 0, rounded)
    return np.ascontiguousarray(rounded, dtype=np.uint16), saturation


def _segmented_matrix_block(
    inputs: np.ndarray[Any, Any],
    weights: np.ndarray[Any, Any],
) -> tuple[np.ndarray[Any, Any], int]:
    if inputs.shape[0] != 1 or weights.shape[0] != N_TILE:
        raise QwenFullModelReferenceError("independent matrix block shape differs")
    if inputs.shape[1] != weights.shape[1] or inputs.shape[1] % K_TILE:
        raise QwenFullModelReferenceError("independent matrix reduction differs")
    input_values = _decode(inputs)
    weight_values = _decode(weights)
    accumulator = np.zeros((1, N_TILE), dtype=np.float32)
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        for start in range(0, inputs.shape[1], K_TILE):
            products = np.multiply(
                input_values[:, None, start : start + K_TILE],
                weight_values[None, :, start : start + K_TILE],
                dtype=np.float32,
            )
            if not np.all(np.isfinite(products)):
                raise QwenFullModelReferenceError(
                    "independent BF16 multiplication overflowed binary32"
                )
            products[products == 0] = np.float32(0.0)
            ordered = np.concatenate((accumulator[:, :, None], products), axis=2)
            accumulator = np.add.accumulate(ordered, axis=2, dtype=np.float32)[:, :, -1]
            if not np.all(np.isfinite(accumulator)):
                raise QwenFullModelReferenceError(
                    "independent BF16 accumulation overflowed binary32"
                )
    finally:
        np.seterr(**previous)
    return _encode(accumulator)


def _matrix(
    reader: LockedCheckpointReader,
    tensor_name: str,
    inputs: np.ndarray[Any, Any],
) -> tuple[np.ndarray[Any, Any], int, tuple[int, int]]:
    record = reader.tensor_record(tensor_name)
    if (
        record["dtype"] != "BF16"
        or not isinstance(record["shape"], list)
        or len(record["shape"]) != 2
    ):
        raise QwenFullModelReferenceError(
            f"matrix weight {tensor_name!r} metadata differs"
        )
    n, k = (int(item) for item in record["shape"])
    if (
        n % N_TILE
        or k % K_TILE
        or inputs.shape != (1, k)
        or record["size_bytes"] != n * k * BF16_BYTES
    ):
        raise QwenFullModelReferenceError(
            f"matrix weight {tensor_name!r} geometry differs"
        )
    block_bytes = N_TILE * k * BF16_BYTES
    blocks: list[np.ndarray[Any, Any]] = []
    saturation = 0
    first_weight_row: np.ndarray[Any, Any] | None = None

    def consume(chunk: bytes) -> None:
        nonlocal saturation, first_weight_row
        if len(chunk) != block_bytes:
            raise QwenFullModelReferenceError(
                f"matrix weight {tensor_name!r} block is incomplete"
            )
        weights = _codes(chunk, (N_TILE, k), f"matrix weight {tensor_name}")
        if first_weight_row is None:
            first_weight_row = weights[0].copy()
        values, block_saturation = _segmented_matrix_block(inputs, weights)
        blocks.append(values)
        saturation += block_saturation

    reader.consume_tensor_payload(tensor_name, consume, chunk_bytes=block_bytes)
    if len(blocks) != n // N_TILE or first_weight_row is None:
        raise QwenFullModelReferenceError(
            f"matrix weight {tensor_name!r} output coverage differs"
        )
    output = np.concatenate(blocks, axis=1)
    try:
        selected = dense_bf16_linear_selected_rows_bf16(
            inputs.tolist(),
            [first_weight_row.tolist()],
            output_row_indices=[0],
            declared_output_count=n,
        )
    except BF16MatrixReferenceError as exc:
        raise QwenFullModelReferenceError(
            f"matrix scalar cross-check failed for {tensor_name!r}: {exc}"
        ) from exc
    if int(output[0, 0]) != selected.values[0][0]:
        raise QwenFullModelReferenceError(
            f"matrix selected scalar row differs for {tensor_name!r}"
        )
    return output, saturation, (n, k)


def _silu(
    gate: np.ndarray[Any, Any],
    up: np.ndarray[Any, Any],
) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any], int, int]:
    gate_flat = np.ascontiguousarray(gate, dtype=np.uint16).reshape(-1)
    up_flat = np.ascontiguousarray(up, dtype=np.uint16).reshape(-1)
    if gate_flat.shape != up_flat.shape:
        raise QwenFullModelReferenceError("independent SiLU operand shapes differ")
    unique, inverse, counts = np.unique(
        gate_flat, return_inverse=True, return_counts=True
    )
    activation_codes = np.empty(unique.shape, dtype=np.uint16)
    activation_saturation = 0
    try:
        for index, (code, count) in enumerate(zip(unique, counts, strict=True)):
            scalar = qwen3_silu_mul_bf16([[int(code)]], [[0x3F80]])
            activation = int(scalar.activation_values[0][0])
            if int(scalar.values[0][0]) != activation:
                raise QwenFullModelReferenceError(
                    "scalar SiLU unit-weight result differs from its activation"
                )
            activation_codes[index] = activation
            activation_saturation += scalar.activation_saturated_element_count * int(
                count
            )
    except ElementwiseReferenceError as exc:
        raise QwenFullModelReferenceError(
            f"independent SiLU activation failed: {exc}"
        ) from exc
    activations = activation_codes[inverse].reshape(gate.shape)
    product_values = np.multiply(_decode(activations), _decode(up), dtype=np.float32)
    output, output_saturation = _encode(product_values)

    indices = sorted({0, gate_flat.size // 2, gate_flat.size - 1})
    for index in indices:
        try:
            scalar = qwen3_silu_mul_bf16(
                [[int(gate_flat[index])]], [[int(up_flat[index])]]
            )
        except ElementwiseReferenceError as exc:
            raise QwenFullModelReferenceError(
                f"independent selected SiLU failed at {index}: {exc}"
            ) from exc
        if (
            int(activations.reshape(-1)[index]) != scalar.activation_values[0][0]
            or int(output.reshape(-1)[index]) != scalar.values[0][0]
        ):
            raise QwenFullModelReferenceError(
                f"independent selected SiLU differs at element {index}"
            )
    return activations, output, activation_saturation, output_saturation


def _event(
    observed: Mapping[str, Any],
    operation: ProductionOperation,
    *,
    command_start: int,
    command_count: int,
    outputs: Mapping[str, Any],
    diagnostics: Mapping[str, Any] | None = None,
    logical_index: int | None = None,
) -> None:
    expected: dict[str, Any] = {
        "command_count": command_count,
        "command_start": command_start,
        "kernel_index": operation.index,
        "kind": operation.kind,
        "operation_id": operation.operation_id,
        "outputs": dict(outputs),
    }
    if diagnostics is not None:
        expected["diagnostics"] = dict(diagnostics)
    if logical_index is not None:
        expected["logical_index"] = logical_index
    if dict(observed) != expected:
        raise QwenFullModelReferenceError(
            f"first execution divergence at {operation.operation_id!r}: "
            f"observed={dict(observed)!r}, expected={expected!r}"
        )


def _command(counters: Counter[str], opcode: str, count: int = 1) -> None:
    counters[f"commands.{opcode}"] += count
    counters["commands.total"] += count


def check_qwen_full_model_execution(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    request_path: Path,
    execution_report_path: Path,
) -> dict[str, Any]:
    """Independently execute and check one fixed complete-model request."""

    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        model = load_production_model_graph(Path(model_graph_path))
        capability = load_production_capability(Path(capability_path))
        request = _canonical(Path(request_path), "execution request")
        report = _canonical(Path(execution_report_path), "execution report")
    except (
        CheckpointError,
        OSError,
        ProductionCapabilityError,
        ProductionModelGraphError,
    ) as exc:
        raise QwenFullModelReferenceError(
            f"cannot admit independent Qwen reference inputs: {exc}"
        ) from exc
    _identity(request, "request_id", "execution request")
    _identity(report, "report_id", "execution report")
    _exact(
        request,
        {
            "expected_generations",
            "graph_id",
            "last_row_index",
            "phase",
            "position_end",
            "position_start",
            "request_id",
            "schema",
            "span_tokens",
            "token_id",
            "transaction_id",
        },
        set(),
        "execution request",
    )
    _exact(
        report,
        {
            "artifact_admission",
            "build_id",
            "capability_id",
            "claim_boundary",
            "command_abi",
            "command_count",
            "command_program_sha256",
            "counter_reconciliation",
            "counters",
            "events",
            "graph_id",
            "hbm_logical_sha256",
            "independent_check_id",
            "kernel_ir_id",
            "layer_outputs",
            "mode",
            "operation_count",
            "outputs",
            "physical_plan_id",
            "report_id",
            "request_id",
            "saturation",
            "schema",
            "simulator_version",
            "source_lock_id",
            "state",
            "status",
            "timing",
        },
        set(),
        "execution report",
    )
    if (
        model.model_id != MODEL_ID
        or len(model.operations) != OPERATION_COUNT
        or len(model.tensors) != TENSOR_COUNT
        or len(model.state_resources) != STATE_COUNT
        or lock["checkpoint"].get("tensor_count") != WEIGHT_COUNT
        or request.get("schema") != REQUEST_SCHEMA
        or request.get("graph_id") != model.graph_id
        or request.get("token_id") != 0
        or request.get("position_start") != 0
        or request.get("position_end") != 1
        or request.get("span_tokens") != 1
        or request.get("phase") != "prefill"
        or request.get("last_row_index") != 0
        or request.get("expected_generations") != [0] * STATE_COUNT
    ):
        raise QwenFullModelReferenceError(
            "independent fixed request or model boundary differs"
        )
    if (
        report.get("schema") != EXECUTION_SCHEMA
        or report.get("status") != "pass"
        or report.get("mode") != "artifact_only_data_bearing_functional"
        or report.get("simulator_version") != SIMULATOR_VERSION
        or report.get("artifact_admission")
        != {
            "all_hbm_shards_sha256_verified": True,
            "non_hbm_manifest_artifacts_sha256_verified": True,
        }
        or report.get("command_abi") != {"major": 2, "minor": 5}
        or report.get("counter_reconciliation")
        != "complete_observed_command_and_numeric_counts"
        or report.get("timing")
        != {"reason": "capability_uncharacterized", "status": "unavailable"}
        or report.get("graph_id") != model.graph_id
        or report.get("capability_id") != capability.capability_id
        or report.get("request_id") != request["request_id"]
        or report.get("operation_count") != OPERATION_COUNT
        or report.get("command_count") != 924386
        or report.get("claim_boundary")
        != {
            "complete_model_one_token_execution": True,
            "decode_steps": 0,
            "exact_8000_token_acceptance": False,
            "timing_or_performance": False,
        }
    ):
        raise QwenFullModelReferenceError("execution report boundary differs")
    events = report.get("events")
    if not isinstance(events, list) or len(events) != OPERATION_COUNT:
        raise QwenFullModelReferenceError("execution event coverage differs")

    data: dict[str, np.ndarray[Any, Any]] = {}
    captures: dict[str, dict[str, Any]] = {}
    states: dict[str, KVSnapshotReference] = {
        f"kv.layer.{layer}": empty_kv_snapshot(
            f"kv.layer.{layer}", capacity=CONTEXT_CAPACITY
        )
        for layer in range(LAYER_COUNT)
    }
    prepared: dict[str, PreparedKVReference] = {}
    state_handles: dict[str, str] = {}
    saturation: dict[str, int] = {}
    counters: Counter[str] = Counter()
    command_start = 0
    burst = capability.hbm.burst_bytes

    def store(tensor_id: str, values: object) -> dict[str, Any]:
        array = np.ascontiguousarray(values, dtype=np.uint16)
        data[tensor_id] = array
        record = _capture(array)
        captures[tensor_id] = record
        return record

    def dma_read(size: int) -> None:
        counters["hbm.useful_bytes_read"] += size
        counters["hbm.transferred_bytes_read"] += align_up(size, burst)
        counters["sram.dma_bytes_written"] += size

    try:
        with LockedCheckpointReader(Path(snapshot), lock) as reader:
            for operation in model.operations:
                outputs: dict[str, Any]
                diagnostics: dict[str, Any] | None = None
                logical_index: int | None = None

                if operation.kind == "EMBEDDING_LOOKUP":
                    weight_name = operation.inputs[1]
                    row_bytes = HIDDEN_WIDTH * BF16_BYTES
                    payload, record = _read_slice(
                        reader,
                        weight_name,
                        start=request["token_id"] * row_bytes,
                        size=row_bytes,
                    )
                    if record["shape"] != [VOCABULARY_SIZE, HIDDEN_WIDTH]:
                        raise QwenFullModelReferenceError(
                            "embedding checkpoint geometry differs"
                        )
                    values = _codes(payload, (1, HIDDEN_WIDTH), "embedding row")
                    outputs = {
                        operation.outputs[0]: store(operation.outputs[0], values)
                    }
                    logical_index = request["token_id"]
                    command_count = 1
                    _command(counters, "DMA_HBM_INDEXED_TO_SRAM")
                    dma_read(row_bytes)

                elif operation.kind == "RMS_NORM":
                    width = int(operation.attributes["normalization_width"])
                    if operation.attributes.get("epsilon") != 1e-6:
                        raise QwenFullModelReferenceError(
                            f"RMSNorm epsilon for {operation.operation_id!r} differs"
                        )
                    inputs = data[operation.inputs[0]].reshape(-1, width)
                    payload, record = _read_tensor(reader, operation.inputs[1])
                    if record["shape"] != [width]:
                        raise QwenFullModelReferenceError(
                            f"RMSNorm weight for {operation.operation_id!r} differs"
                        )
                    weights = _codes(payload, (width,), "RMSNorm weight")
                    try:
                        result = rms_norm_bf16(
                            inputs.tolist(),
                            weights.tolist(),
                            epsilon_code=EPSILON_CODE,
                        )
                    except RMSNormReferenceError as exc:
                        raise QwenFullModelReferenceError(
                            f"RMSNorm reference failed at {operation.operation_id}: {exc}"
                        ) from exc
                    values = np.asarray(result.values, dtype=np.uint16)
                    outputs = {
                        operation.outputs[0]: store(operation.outputs[0], values)
                    }
                    diagnostics = {
                        "inverse_rms_sha256": hashlib.sha256(
                            _u32_payload(result.inverse_rms_codes)
                        ).hexdigest(),
                        "mean_square_sha256": hashlib.sha256(
                            _u32_payload(result.mean_square_codes)
                        ).hexdigest(),
                        "normalized_sha256": hashlib.sha256(
                            _payload(result.normalized_values)
                        ).hexdigest(),
                    }
                    saturation[str(operation.index)] = (
                        result.normalized_saturated_element_count
                        + result.output_saturated_element_count
                    )
                    rows = inputs.shape[0]
                    elements = rows * width
                    command_count = 2
                    _command(counters, "DMA_HBM_TO_SRAM")
                    _command(counters, "RMSNORM_BF16")
                    dma_read(len(payload))
                    counters["sram.rmsnorm_input_bytes_read"] += elements * 2
                    counters["sram.rmsnorm_weight_bytes_read"] += len(payload)
                    counters["sram.rmsnorm_output_bytes_written"] += elements * 2
                    counters["arithmetic.rmsnorm_squares"] += elements
                    counters["arithmetic.rmsnorm_reduction_additions"] += rows * (
                        width - 1
                    )
                    counters["arithmetic.rmsnorm_mean_divisions"] += rows
                    counters["arithmetic.rmsnorm_epsilon_additions"] += rows
                    counters["arithmetic.rmsnorm_rsqrt"] += rows
                    counters["arithmetic.rmsnorm_normalization_multiplications"] += (
                        elements
                    )
                    counters["arithmetic.rmsnorm_weight_multiplications"] += elements

                elif operation.kind == "MATMUL":
                    inputs = data[operation.inputs[0]].reshape(1, -1)
                    values, matrix_saturation, (n, k) = _matrix(
                        reader, operation.inputs[1], inputs
                    )
                    outputs = {
                        operation.outputs[0]: store(operation.outputs[0], values)
                    }
                    saturation[str(operation.index)] = matrix_saturation
                    tiles = (n // N_TILE) * (k // K_TILE)
                    command_count = 2 * tiles
                    _command(counters, "DMA_HBM_TO_SRAM", tiles)
                    _command(counters, "MATMUL_BF16_TILE", tiles)
                    weight_bytes = n * k * BF16_BYTES
                    dma_read(weight_bytes)
                    counters["matrix.input_bytes_read"] += tiles * K_TILE * 2
                    counters["matrix.weight_bytes_read"] += weight_bytes
                    counters["matrix.accumulator_bytes_read"] += (
                        (n // N_TILE) * (k // K_TILE - 1) * N_TILE * 4
                    )
                    counters["matrix.accumulator_bytes_written"] += tiles * N_TILE * 4
                    counters["matrix.output_bytes_written"] += n * 2
                    counters["matrix.fused_output_blocks"] += n // N_TILE
                    counters["arithmetic.matrix_multiplications"] += n * k
                    counters["arithmetic.matrix_accumulation_additions"] += n * k

                elif operation.kind == "ROPE":
                    query = data[operation.inputs[0]].reshape(QUERY_HEADS, HEAD_DIM)
                    key = data[operation.inputs[1]].reshape(KEY_VALUE_HEADS, HEAD_DIM)
                    cosine = [0x3F80] * HEAD_DIM
                    sine = [0] * HEAD_DIM
                    try:
                        result = rope_bf16(query.tolist(), key.tolist(), cosine, sine)
                    except RoPEReferenceError as exc:
                        raise QwenFullModelReferenceError(
                            f"RoPE reference failed at {operation.operation_id}: {exc}"
                        ) from exc
                    outputs = {
                        operation.outputs[0]: store(
                            operation.outputs[0], result.query_values
                        ),
                        operation.outputs[1]: store(
                            operation.outputs[1], result.key_values
                        ),
                    }
                    saturation[str(operation.index)] = (
                        result.multiplication_saturated_element_count
                        + result.addition_saturated_element_count
                    )
                    command_count = 2
                    _command(counters, "DMA_HBM_INDEXED_TO_SRAM")
                    _command(counters, "ROPE_BF16")
                    coefficient_bytes = 2 * HEAD_DIM * BF16_BYTES
                    dma_read(coefficient_bytes)
                    elements = (QUERY_HEADS + KEY_VALUE_HEADS) * HEAD_DIM
                    counters["sram.rope_input_bytes_read"] += (
                        query.size * 2 + key.size * 2 + coefficient_bytes
                    )
                    counters["sram.rope_output_bytes_written"] += elements * 2
                    counters["arithmetic.rope_multiplications"] += 2 * elements
                    counters["arithmetic.rope_additions"] += elements

                elif operation.kind == "KV_PREPARE":
                    resource_id = next(
                        effect.state_id
                        for effect in operation.effects
                        if effect.action == "prepare"
                    )
                    key = data[operation.inputs[0]].reshape(
                        1, KEY_VALUE_HEADS, HEAD_DIM
                    )
                    value = data[operation.inputs[1]].reshape(
                        1, KEY_VALUE_HEADS, HEAD_DIM
                    )
                    try:
                        transaction = prepare_kv_append(
                            states[resource_id],
                            transaction_id=request["transaction_id"],
                            expected_generation=0,
                            position_start=0,
                            key_values=key.tolist(),
                            value_values=value.tolist(),
                        )
                    except AttentionReferenceError as exc:
                        raise QwenFullModelReferenceError(
                            f"KV reference failed at {operation.operation_id}: {exc}"
                        ) from exc
                    prepared[resource_id] = transaction
                    state_handles[operation.outputs[0]] = resource_id
                    key_payload = _payload(key)
                    value_payload = _payload(value)
                    outputs = {
                        operation.outputs[0]: {
                            "key_payload_sha256": hashlib.sha256(
                                key_payload
                            ).hexdigest(),
                            "resource_id": resource_id,
                            "transaction_private": True,
                            "value_payload_sha256": hashlib.sha256(
                                value_payload
                            ).hexdigest(),
                        }
                    }
                    command_count = 1
                    _command(counters, "KV_PREPARE_BF16")
                    payload_bytes = len(key_payload) + len(value_payload)
                    counters["sram.kv_prepare_bytes_read"] += payload_bytes
                    counters["state.payload_bytes_written"] += payload_bytes
                    counters["hbm.useful_bytes_written"] += payload_bytes
                    counters["hbm.transferred_bytes_written"] += payload_bytes
                    counters["state.metadata_bytes_read"] += 2 * STATE_METADATA_BYTES

                elif operation.kind == "ATTENTION":
                    resource_id = next(
                        effect.state_id
                        for effect in operation.effects
                        if effect.action == "read_prepared"
                    )
                    if state_handles.get(operation.inputs[1]) != resource_id:
                        raise QwenFullModelReferenceError(
                            "reference attention state handle differs"
                        )
                    query = data[operation.inputs[0]].reshape(1, QUERY_HEADS, HEAD_DIM)
                    try:
                        result = gqa_causal_attention_bf16(
                            query.tolist(), states[resource_id], prepared[resource_id]
                        )
                    except AttentionReferenceError as exc:
                        raise QwenFullModelReferenceError(
                            f"attention reference failed at {operation.operation_id}: {exc}"
                        ) from exc
                    values = np.asarray(result.output_values, dtype=np.uint16)
                    outputs = {
                        operation.outputs[0]: store(operation.outputs[0], values)
                    }
                    diagnostics = {
                        "probability_payload_sha256": hashlib.sha256(
                            _payload(result.probability_values)
                        ).hexdigest(),
                        "scaled_score_payload_sha256": hashlib.sha256(
                            _payload(result.scaled_score_values)
                        ).hexdigest(),
                    }
                    saturation[str(operation.index)] = (
                        result.mask_saturated_element_count
                        + result.output_saturated_element_count
                        + result.probability_saturated_element_count
                        + result.scaling_saturated_element_count
                        + result.score_saturated_element_count
                    )
                    command_count = 1
                    _command(counters, "GQA_ATTENTION_BF16")
                    visible = (
                        (states[resource_id].length + 1)
                        * 2
                        * (KEY_VALUE_HEADS * HEAD_DIM * BF16_BYTES)
                    )
                    counters["state.payload_bytes_read"] += visible
                    counters["hbm.useful_bytes_read"] += visible
                    counters["hbm.transferred_bytes_read"] += visible
                    counters["sram.attention_query_bytes_read"] += query.size * 2
                    counters["sram.attention_output_bytes_written"] += values.size * 2
                    for name, count in asdict(result.accounting).items():
                        counters[f"arithmetic.attention_{name}"] += count

                elif operation.kind == "ADD":
                    left = data[operation.inputs[0]].reshape(1, -1)
                    right = data[operation.inputs[1]].reshape(1, -1)
                    try:
                        result = bf16_add_rne(left.tolist(), right.tolist())
                    except ElementwiseReferenceError as exc:
                        raise QwenFullModelReferenceError(
                            f"ADD reference failed at {operation.operation_id}: {exc}"
                        ) from exc
                    values = np.asarray(result.values, dtype=np.uint16)
                    outputs = {
                        operation.outputs[0]: store(operation.outputs[0], values)
                    }
                    saturation[str(operation.index)] = (
                        result.output_saturated_element_count
                    )
                    command_count = 1
                    _command(counters, "ADD_BF16")
                    counters["sram.add_input_bytes_read"] += (
                        left.size + right.size
                    ) * 2
                    counters["sram.add_output_bytes_written"] += values.size * 2
                    counters["arithmetic.residual_additions"] += values.size

                elif operation.kind == "SILU_MUL":
                    gate = data[operation.inputs[0]].reshape(1, -1)
                    up = data[operation.inputs[1]].reshape(1, -1)
                    activation, values, activation_sat, output_sat = _silu(gate, up)
                    outputs = {
                        operation.outputs[0]: store(operation.outputs[0], values)
                    }
                    diagnostics = {
                        "activation_payload_sha256": hashlib.sha256(
                            _payload(activation)
                        ).hexdigest()
                    }
                    saturation[str(operation.index)] = activation_sat + output_sat
                    command_count = 1
                    _command(counters, "SILU_MUL_BF16")
                    counters["sram.silu_input_bytes_read"] += (gate.size + up.size) * 2
                    counters["sram.silu_output_bytes_written"] += values.size * 2
                    counters["arithmetic.sigmoid_exponentials"] += values.size
                    counters["arithmetic.sigmoid_denominator_additions"] += values.size
                    counters["arithmetic.sigmoid_divisions"] += values.size
                    counters["arithmetic.silu_multiplications"] += values.size
                    counters["arithmetic.up_gate_multiplications"] += values.size

                elif operation.kind == "LAST_TOKEN_SELECT":
                    values = data[operation.inputs[0]].reshape(1, -1)
                    try:
                        result = last_token_select_bf16(values.tolist(), logical_rows=1)
                    except SelectionReferenceError as exc:
                        raise QwenFullModelReferenceError(
                            f"selection reference failed: {exc}"
                        ) from exc
                    selected = np.asarray(result.values, dtype=np.uint16)
                    outputs = {
                        operation.outputs[0]: store(operation.outputs[0], selected)
                    }
                    logical_index = result.index
                    command_count = 1
                    _command(counters, "DMA_SRAM_INDEXED_TO_SRAM")
                    counters["sram.selection_index_bytes_read"] += 4
                    counters["sram.selection_input_bytes_read"] += selected.size * 2
                    counters["sram.selection_output_bytes_written"] += selected.size * 2

                elif operation.kind == "STATE_COMMIT":
                    resources = [f"kv.layer.{layer}" for layer in range(LAYER_COUNT)]
                    try:
                        committed = commit_kv_group(
                            tuple(
                                (states[resource], prepared[resource])
                                for resource in resources
                            )
                        )
                    except AttentionReferenceError as exc:
                        raise QwenFullModelReferenceError(
                            f"state commit reference failed: {exc}"
                        ) from exc
                    states = {state.resource_id: state for state in committed}
                    logits = data[operation.inputs[0]]
                    outputs = {
                        operation.outputs[0]: store(operation.outputs[0], logits)
                    }
                    command_count = 1
                    _command(counters, "STATE_COMMIT")
                    counters["state.metadata_bytes_read"] += (
                        2 * STATE_METADATA_BYTES * STATE_COUNT
                    )
                    counters["state.metadata_bytes_written"] += (
                        STATE_METADATA_BYTES * STATE_COUNT
                    )
                    counters["hbm.useful_bytes_written"] += (
                        STATE_METADATA_BYTES * STATE_COUNT
                    )
                    counters["hbm.transferred_bytes_written"] += (
                        STATE_METADATA_BYTES * STATE_COUNT
                    )

                else:
                    raise QwenFullModelReferenceError(
                        f"unsupported reference operation {operation.kind!r}"
                    )

                _event(
                    events[operation.index],
                    operation,
                    command_start=command_start,
                    command_count=command_count,
                    outputs=outputs,
                    diagnostics=diagnostics,
                    logical_index=logical_index,
                )
                command_start += command_count

            if len(reader.accessed_tensor_names) != WEIGHT_COUNT:
                raise QwenFullModelReferenceError(
                    "independent checkpoint tensor coverage differs: "
                    f"{len(reader.accessed_tensor_names)}"
                )
    except CheckpointError as exc:
        raise QwenFullModelReferenceError(
            f"independent checkpoint execution failed: {exc}"
        ) from exc

    _command(counters, "COMPLETE")
    if command_start + 1 != 924386:
        raise QwenFullModelReferenceError(
            f"independent command coverage differs: {command_start + 1}"
        )
    expected_counters = dict(sorted(counters.items()))
    if len(expected_counters) != 70:
        raise QwenFullModelReferenceError(
            f"independent counter coverage differs: {len(expected_counters)}"
        )
    if report.get("counters") != expected_counters:
        observed = report.get("counters")
        keys = sorted(set(expected_counters) | set(observed or {}))
        first = next(
            key
            for key in keys
            if not isinstance(observed, dict)
            or observed.get(key) != expected_counters.get(key)
        )
        raise QwenFullModelReferenceError(
            f"first counter divergence at {first!r}: "
            f"observed={None if not isinstance(observed, dict) else observed.get(first)!r}, "
            f"expected={expected_counters.get(first)!r}"
        )
    expected_saturation = {
        "by_kernel": dict(sorted(saturation.items(), key=lambda item: int(item[0]))),
        "total": sum(saturation.values()),
    }
    if len(expected_saturation["by_kernel"]) != 578:
        raise QwenFullModelReferenceError(
            "independent saturation-kernel coverage differs"
        )
    if report.get("saturation") != expected_saturation:
        raise QwenFullModelReferenceError("complete saturation accounting differs")

    layer_outputs = [
        {"layer": layer, "tensor_id": f"hidden.{layer}", **captures[f"hidden.{layer}"]}
        for layer in range(1, LAYER_COUNT + 1)
    ]
    if report.get("layer_outputs") != layer_outputs:
        raise QwenFullModelReferenceError("complete layer-output hashes differ")
    logits = data["output.committed_logits"].reshape(-1)
    logits_values = (logits.astype(np.uint32) << np.uint32(16)).view(np.float32)
    greedy_token = int(np.argmax(logits_values))
    maximum_count = int(np.count_nonzero(logits_values == logits_values[greedy_token]))
    if maximum_count != 1:
        raise QwenFullModelReferenceError(
            "independent greedy logit maximum is not unique"
        )
    expected_outputs = {
        "committed_logits": {
            **captures["output.committed_logits"],
            "greedy_maximum_count": maximum_count,
            "greedy_token_id": greedy_token,
        },
        "final_normalization": captures["hidden.final_norm"],
        "hidden_36": captures["hidden.36"],
        "last_token": captures["hidden.last_token"],
    }
    if report.get("outputs") != expected_outputs:
        raise QwenFullModelReferenceError("complete final outputs differ")
    state_report = []
    for layer in range(LAYER_COUNT):
        resource = f"kv.layer.{layer}"
        state = states[resource]
        state_report.append(
            {
                "generation": state.generation,
                "key_payload_sha256": hashlib.sha256(
                    _payload(state.key_values)
                ).hexdigest(),
                "layer": layer,
                "length": state.length,
                "resource_id": resource,
                "value_payload_sha256": hashlib.sha256(
                    _payload(state.value_values)
                ).hexdigest(),
            }
        )
    if report.get("state") != state_report:
        raise QwenFullModelReferenceError("complete committed KV state differs")

    body = {
        "capability_id": capability.capability_id,
        "checkpoint_lock_id": lock["lock_id"],
        "checks": {
            "all_399_checkpoint_tensors_authenticated": True,
            "all_617_operation_outputs_exact": True,
            "all_36_layer_boundaries_exact": True,
            "all_36_prepared_and_committed_states_exact": True,
            "all_70_counters_independently_derived": True,
            "complete_logits_and_unique_greedy_token_exact": True,
            "independent_scalar_kernel_cross_checks": True,
            "row_major_checkpoint_not_tiled_hbm_source": True,
            "segmented_k_not_fused_matrix_execution": True,
        },
        "counter_sha256": sha256_bytes(canonical_json_bytes(expected_counters)),
        "execution_report_id": report["report_id"],
        "graph_id": model.graph_id,
        "layer_outputs": layer_outputs,
        "outputs": expected_outputs,
        "reference_version": REFERENCE_VERSION,
        "request_id": request["request_id"],
        "saturation": expected_saturation,
        "schema": REFERENCE_SCHEMA,
        "state": state_report,
        "status": "pass",
    }
    return {**body, "reference_id": sha256_bytes(canonical_json_bytes(body))}


def publish_qwen_full_model_reference(report: Mapping[str, Any], output: Path) -> None:
    """Publish one canonical independent-reference result without overwrite."""

    value = dict(report)
    if value.get("schema") != REFERENCE_SCHEMA or value.get("status") != "pass":
        raise QwenFullModelReferenceError("reference report boundary differs")
    _identity(value, "reference_id", "reference report")
    path = Path(output)
    if path.exists():
        raise QwenFullModelReferenceError(f"reference report already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


__all__ = [
    "QwenFullModelReferenceError",
    "REFERENCE_SCHEMA",
    "REFERENCE_VERSION",
    "check_qwen_full_model_execution",
    "publish_qwen_full_model_reference",
]
