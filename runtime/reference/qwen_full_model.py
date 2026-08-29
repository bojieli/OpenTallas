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
import struct
from typing import Any, Callable, Mapping

import numpy as np
from tokenizers import Tokenizer, __version__ as tokenizers_version

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
    sha256_file,
)
from compiler.tensor_accelerator.hbm_shards import HBMShardError, HBMShardReader
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
DYNAMIC_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_dynamic_execution.v1"
)
DYNAMIC_REQUEST_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_dynamic_request.v1"
)
DYNAMIC_SESSION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_dynamic_session.v1"
)
DYNAMIC_SESSION_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_dynamic_session_execution.v1"
)
DYNAMIC_SESSION_REFERENCE_SCHEMA = (
    "opentallas.tensor_accelerator.qwen_full_model_dynamic_session_reference.v1"
)
REFERENCE_VERSION = "tensor-accelerator-qwen-full-model-reference-0.1.0"
DYNAMIC_REFERENCE_VERSION = "tensor-accelerator-qwen-dynamic-session-reference-0.1.0"
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
STATE_MAGIC = b"OTTAKV23"
TRANSACTION_MAGIC = b"OTTATX23"
STATE_METADATA = struct.Struct("<8sQQQQQQ8s")
TRANSACTION_DESCRIPTOR = struct.Struct("<8sQQQQQQ8s")
TOKENIZERS_VERSION = "0.22.2"


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


def _check_qwen_full_model_transaction(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    capability_path: Path,
    request_path: Path,
    execution_report_path: Path,
    dynamic_session: Mapping[str, Any] | None = None,
    initial_states: Mapping[str, KVSnapshotReference] | None = None,
    rope_coefficients: np.ndarray[Any, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, KVSnapshotReference]]:
    """Independently execute and check one fixed or dynamic model transaction."""

    dynamic = dynamic_session is not None

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
    fixed_request_keys = {
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
    }
    dynamic_request_keys = {
        "build_id",
        "command_program_sha256",
        "expected_generations",
        "expected_lengths",
        "generated_token_index",
        "graph_id",
        "input_role",
        "last_row_index",
        "output_role",
        "phase",
        "position_end",
        "position_start",
        "previous_report_id",
        "request_id",
        "request_version",
        "schema",
        "session_id",
        "span_tokens",
        "step_index",
        "token_id",
        "transaction_id",
    }
    report_keys = {
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
    }
    dynamic_report_keys = report_keys | {
        "input",
        "previous_report_id",
        "runtime_binding",
        "session_id",
        "state_before",
        "step_index",
    }
    _exact(
        request,
        dynamic_request_keys if dynamic else fixed_request_keys,
        set(),
        "execution request",
    )
    _exact(
        report,
        dynamic_report_keys if dynamic else report_keys,
        set(),
        "execution report",
    )
    position = request.get("position_start")
    token_id = request.get("token_id")
    if (
        model.model_id != MODEL_ID
        or len(model.operations) != OPERATION_COUNT
        or len(model.tensors) != TENSOR_COUNT
        or len(model.state_resources) != STATE_COUNT
        or lock["checkpoint"].get("tensor_count") != WEIGHT_COUNT
        or request.get("graph_id") != model.graph_id
        or isinstance(token_id, bool)
        or not isinstance(token_id, int)
        or not 0 <= token_id < VOCABULARY_SIZE
        or isinstance(position, bool)
        or not isinstance(position, int)
        or not 0 <= position < CONTEXT_CAPACITY
        or request.get("position_end") != position + 1
        or request.get("span_tokens") != 1
        or request.get("last_row_index") != 0
    ):
        raise QwenFullModelReferenceError(
            "independent request or model boundary differs"
        )
    if dynamic:
        assert dynamic_session is not None
        expected_phase = (
            "prefill"
            if position < dynamic_session["prompt"]["token_count"]
            else "decode"
        )
        expected_input_role = "prompt" if expected_phase == "prefill" else "generated"
        expected_generated_index = (
            None
            if position < dynamic_session["prompt"]["token_count"] - 1
            else position - dynamic_session["prompt"]["token_count"] + 1
        )
        expected_output_role = (
            "prefill_intermediate"
            if expected_generated_index is None
            else "generated_token"
        )
        if (
            request.get("schema") != DYNAMIC_REQUEST_SCHEMA
            or request.get("session_id") != dynamic_session.get("session_id")
            or request.get("build_id") != dynamic_session.get("build_id")
            or request.get("command_program_sha256")
            != dynamic_session.get("command_program_sha256")
            or request.get("step_index") != position
            or request.get("phase") != expected_phase
            or request.get("input_role") != expected_input_role
            or request.get("output_role") != expected_output_role
            or request.get("generated_token_index") != expected_generated_index
            or request.get("expected_generations") != [position] * STATE_COUNT
            or request.get("expected_lengths") != [position] * STATE_COUNT
        ):
            raise QwenFullModelReferenceError(
                "independent dynamic request boundary differs"
            )
        expected_claim = {
            "complete_model_one_token_execution": True,
            "exact_8000_token_acceptance": False,
            "generated_token_decision": expected_output_role == "generated_token",
            "session_generation_complete": False,
            "timing_or_performance": False,
        }
        expected_input = {
            "generated_token_index": expected_generated_index,
            "input_role": expected_input_role,
            "output_role": expected_output_role,
            "phase": expected_phase,
            "position_end": position + 1,
            "position_start": position,
            "token_id": token_id,
        }
        expected_report_schema = DYNAMIC_EXECUTION_SCHEMA
        expected_report_mode = "artifact_only_data_bearing_dynamic_transaction"
        if (
            report.get("session_id") != dynamic_session.get("session_id")
            or report.get("step_index") != position
            or report.get("previous_report_id") != request.get("previous_report_id")
            or report.get("input") != expected_input
            or report.get("state_before")
            != {
                "generations": [position] * STATE_COUNT,
                "lengths": [position] * STATE_COUNT,
            }
        ):
            raise QwenFullModelReferenceError(
                "independent dynamic report chain boundary differs"
            )
    else:
        if (
            request.get("schema") != REQUEST_SCHEMA
            or token_id != 0
            or position != 0
            or request.get("phase") != "prefill"
            or request.get("expected_generations") != [0] * STATE_COUNT
            or initial_states is not None
            or rope_coefficients is not None
        ):
            raise QwenFullModelReferenceError(
                "independent fixed request boundary differs"
            )
        expected_claim = {
            "complete_model_one_token_execution": True,
            "decode_steps": 0,
            "exact_8000_token_acceptance": False,
            "timing_or_performance": False,
        }
        expected_report_schema = EXECUTION_SCHEMA
        expected_report_mode = "artifact_only_data_bearing_functional"
    if (
        report.get("schema") != expected_report_schema
        or report.get("status") != "pass"
        or report.get("mode") != expected_report_mode
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
        or report.get("claim_boundary") != expected_claim
    ):
        raise QwenFullModelReferenceError("execution report boundary differs")
    events = report.get("events")
    if not isinstance(events, list) or len(events) != OPERATION_COUNT:
        raise QwenFullModelReferenceError("execution event coverage differs")

    data: dict[str, np.ndarray[Any, Any]] = {}
    captures: dict[str, dict[str, Any]] = {}
    if initial_states is None:
        states: dict[str, KVSnapshotReference] = {
            f"kv.layer.{layer}": empty_kv_snapshot(
                f"kv.layer.{layer}", capacity=CONTEXT_CAPACITY
            )
            for layer in range(LAYER_COUNT)
        }
    else:
        states = dict(initial_states)
        expected_resources = {f"kv.layer.{layer}" for layer in range(LAYER_COUNT)}
        if set(states) != expected_resources or any(
            not isinstance(state, KVSnapshotReference)
            or state.resource_id != resource
            or state.generation != position
            or state.length != position
            or state.capacity != CONTEXT_CAPACITY
            for resource, state in states.items()
        ):
            raise QwenFullModelReferenceError(
                "independent dynamic initial state differs"
            )
    prepared: dict[str, PreparedKVReference] = {}
    state_handles: dict[str, str] = {}
    saturation: dict[str, int] = {}
    counters: Counter[str] = Counter()
    command_start = 0
    burst = capability.hbm.burst_bytes
    if rope_coefficients is None:
        cosine_codes = [0x3F80] * HEAD_DIM
        sine_codes = [0] * HEAD_DIM
    else:
        raw_coefficients = np.asarray(rope_coefficients)
        if (
            raw_coefficients.shape != (2 * HEAD_DIM,)
            or raw_coefficients.dtype.kind not in {"i", "u"}
            or np.any(raw_coefficients < 0)
            or np.any(raw_coefficients > 0xFFFF)
        ):
            raise QwenFullModelReferenceError(
                "independent RoPE coefficient row differs"
            )
        coefficient_codes = np.ascontiguousarray(raw_coefficients, dtype=np.uint16)
        if np.any((coefficient_codes & np.uint16(0x7F80)) == np.uint16(0x7F80)):
            raise QwenFullModelReferenceError(
                "independent RoPE coefficient row is not finite"
            )
        cosine_codes = coefficient_codes[:HEAD_DIM].tolist()
        sine_codes = coefficient_codes[HEAD_DIM:].tolist()

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
                    try:
                        result = rope_bf16(
                            query.tolist(), key.tolist(), cosine_codes, sine_codes
                        )
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
                            expected_generation=request["expected_generations"][
                                int(resource_id.rsplit(".", 1)[1])
                            ],
                            position_start=position,
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
    if not dynamic and maximum_count != 1:
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

    common_body = {
        "capability_id": capability.capability_id,
        "checkpoint_lock_id": lock["lock_id"],
        "counter_sha256": sha256_bytes(canonical_json_bytes(expected_counters)),
        "execution_report_id": report["report_id"],
        "graph_id": model.graph_id,
        "layer_outputs": layer_outputs,
        "outputs": expected_outputs,
        "request_id": request["request_id"],
        "saturation": expected_saturation,
        "state": state_report,
        "status": "pass",
    }
    if dynamic:
        body = {
            **common_body,
            "checks": {
                "all_399_checkpoint_tensors_authenticated": True,
                "all_617_operation_outputs_exact": True,
                "all_36_layer_boundaries_exact": True,
                "all_36_prepared_and_committed_states_exact": True,
                "all_70_counters_independently_derived": True,
                "complete_logits_and_lowest_token_id_argmax_exact": True,
                "independent_scalar_kernel_cross_checks": True,
                "row_major_checkpoint_not_tiled_hbm_source": True,
                "segmented_k_not_fused_matrix_execution": True,
            },
            "reference_version": "tensor-accelerator-qwen-dynamic-transaction-reference-0.1.0",
            "session_id": dynamic_session["session_id"],
            "step_index": position,
        }
        evidence = {
            **body,
            "transaction_reference_id": sha256_bytes(canonical_json_bytes(body)),
        }
    else:
        body = {
            **common_body,
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
            "reference_version": REFERENCE_VERSION,
            "schema": REFERENCE_SCHEMA,
        }
        evidence = {
            **body,
            "reference_id": sha256_bytes(canonical_json_bytes(body)),
        }
    return evidence, states


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

    report, _ = _check_qwen_full_model_transaction(
        snapshot=snapshot,
        checkpoint_lock_path=checkpoint_lock_path,
        model_graph_path=model_graph_path,
        capability_path=capability_path,
        request_path=request_path,
        execution_report_path=execution_report_path,
    )
    return report


def _dynamic_transaction_id(request: Mapping[str, Any]) -> int:
    seed = {
        "previous_report_id": request["previous_report_id"],
        "session_id": request["session_id"],
        "step_index": request["step_index"],
        "token_id": request["token_id"],
    }
    transaction = int.from_bytes(
        hashlib.sha256(canonical_json_bytes(seed)).digest()[:8], "big"
    )
    return transaction or 1


def _state_metadata_payload(
    states: Mapping[str, KVSnapshotReference], plan: Mapping[str, Any]
) -> bytes:
    records = bytearray()
    physical_states = plan.get("hbm", {}).get("states")
    if not isinstance(physical_states, list) or len(physical_states) != STATE_COUNT:
        raise QwenFullModelReferenceError(
            "independent physical state table coverage differs"
        )
    for layer, physical in enumerate(physical_states):
        resource = f"kv.layer.{layer}"
        state = states.get(resource)
        if (
            not isinstance(physical, dict)
            or physical.get("layer") != layer
            or physical.get("resource_id") != resource
            or physical.get("max_context_tokens") != CONTEXT_CAPACITY
            or not isinstance(state, KVSnapshotReference)
        ):
            raise QwenFullModelReferenceError(
                "independent physical state ordering differs"
            )
        records.extend(
            STATE_METADATA.pack(
                STATE_MAGIC,
                state.generation,
                state.length,
                state.capacity,
                physical["key_address"],
                physical["value_address"],
                layer,
                bytes(8),
            )
        )
    return bytes(records)


def _transaction_descriptor_payload(
    request: Mapping[str, Any], plan: Mapping[str, Any]
) -> bytes:
    metadata = plan.get("hbm", {}).get("metadata_table")
    if (
        not isinstance(metadata, dict)
        or metadata.get("entry_bytes") != STATE_METADATA.size
        or metadata.get("entry_count") != STATE_COUNT
        or metadata.get("size_bytes") != STATE_COUNT * STATE_METADATA.size
    ):
        raise QwenFullModelReferenceError("independent state metadata table differs")
    records = bytearray()
    for layer in range(LAYER_COUNT):
        records.extend(
            TRANSACTION_DESCRIPTOR.pack(
                TRANSACTION_MAGIC,
                request["transaction_id"],
                request["expected_generations"][layer],
                request["position_start"],
                request["span_tokens"],
                request["position_end"],
                metadata["address"] + layer * STATE_METADATA.size,
                bytes(8),
            )
        )
    return bytes(records)


def _check_runtime_binding(
    report: Mapping[str, Any],
    request: Mapping[str, Any],
    plan: Mapping[str, Any],
    states_before: Mapping[str, KVSnapshotReference],
    states_after: Mapping[str, KVSnapshotReference],
) -> None:
    registers = struct.pack(
        "<IIII",
        request["token_id"],
        request["position_start"],
        request["last_row_index"],
        0,
    )
    metadata_before = _state_metadata_payload(states_before, plan)
    metadata_after = _state_metadata_payload(states_after, plan)
    descriptors = _transaction_descriptor_payload(request, plan)
    expected = {
        "request_registers_sha256": hashlib.sha256(registers).hexdigest(),
        "request_registers_size_bytes": len(registers),
        "state_metadata_after_sha256": hashlib.sha256(metadata_after).hexdigest(),
        "state_metadata_before_sha256": hashlib.sha256(metadata_before).hexdigest(),
        "state_metadata_size_bytes": len(metadata_before),
        "transaction_descriptors_sha256": hashlib.sha256(descriptors).hexdigest(),
        "transaction_descriptors_size_bytes": len(descriptors),
    }
    if report.get("runtime_binding") != expected:
        raise QwenFullModelReferenceError("independent dynamic runtime binding differs")


def _load_rope_table(
    deployment_root: Path, plan: Mapping[str, Any]
) -> tuple[np.ndarray[Any, Any], dict[str, Any]]:
    hbm = plan.get("hbm")
    if not isinstance(hbm, dict):
        raise QwenFullModelReferenceError("independent physical HBM plan is absent")
    coefficient = hbm.get("coefficient_table")
    image = hbm.get("image")
    if (
        not isinstance(coefficient, dict)
        or not isinstance(image, dict)
        or coefficient.get("layout") != "position_major_cos_then_sin_bf16"
        or coefficient.get("positions") != CONTEXT_CAPACITY
        or coefficient.get("row_bytes") != 2 * HEAD_DIM * BF16_BYTES
        or coefficient.get("size_bytes") != CONTEXT_CAPACITY * 2 * HEAD_DIM * BF16_BYTES
        or coefficient.get("offset_bytes") != coefficient.get("address")
        or not isinstance(image.get("shards"), list)
    ):
        raise QwenFullModelReferenceError(
            "independent RoPE coefficient artifact boundary differs"
        )
    try:
        with HBMShardReader(
            Path(deployment_root), image["shards"], verify_hashes=True
        ) as reader:
            if reader.total_size != image.get("size_bytes"):
                raise QwenFullModelReferenceError(
                    "independent logical HBM size differs"
                )
            payload = reader.read(
                coefficient["offset_bytes"], coefficient["size_bytes"]
            )
    except HBMShardError as exc:
        raise QwenFullModelReferenceError(
            f"cannot authenticate the independent RoPE input: {exc}"
        ) from exc
    if hashlib.sha256(payload).hexdigest() != coefficient.get("payload_sha256"):
        raise QwenFullModelReferenceError(
            "independent RoPE coefficient payload differs"
        )
    values = np.frombuffer(payload, dtype="<u2").reshape(CONTEXT_CAPACITY, 2 * HEAD_DIM)
    if np.any((values & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise QwenFullModelReferenceError(
            "independent RoPE coefficient table is not finite"
        )
    return np.ascontiguousarray(values), {
        "all_hbm_shards_sha256_verified": True,
        "layout": coefficient["layout"],
        "payload_sha256": coefficient["payload_sha256"],
        "positions": coefficient["positions"],
        "row_bytes": coefficient["row_bytes"],
        "size_bytes": coefficient["size_bytes"],
    }


def _load_dynamic_tokenizer(
    snapshot: Path, lock: Mapping[str, Any], session: Mapping[str, Any]
) -> Tokenizer:
    records = [
        record
        for record in lock.get("files", [])
        if isinstance(record, dict) and record.get("path") == "tokenizer.json"
    ]
    tokenizer_record = session.get("tokenizer")
    if (
        len(records) != 1
        or not isinstance(tokenizer_record, dict)
        or tokenizer_record
        != {
            "decoded_prompt_exact": True,
            "library": "tokenizers",
            "library_version": TOKENIZERS_VERSION,
            "path": "tokenizer.json",
            "sha256": records[0].get("sha256"),
            "vocabulary_size": VOCABULARY_SIZE,
        }
        or tokenizers_version != TOKENIZERS_VERSION
    ):
        raise QwenFullModelReferenceError(
            "independent dynamic tokenizer manifest differs"
        )
    path = Path(snapshot) / "tokenizer.json"
    digest, size = sha256_file(path)
    if (digest, size) != (records[0].get("sha256"), records[0].get("size_bytes")):
        raise QwenFullModelReferenceError(
            "independent dynamic tokenizer payload differs"
        )
    try:
        tokenizer = Tokenizer.from_file(str(path))
    except Exception as exc:
        raise QwenFullModelReferenceError(
            f"cannot load independent dynamic tokenizer: {exc}"
        ) from exc
    if tokenizer.get_vocab_size(with_added_tokens=True) != 151_669:
        raise QwenFullModelReferenceError(
            "independent dynamic tokenizer vocabulary differs"
        )
    return tokenizer


def check_qwen_dynamic_session_execution(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    deployment_root: Path,
    session_path: Path,
    session_execution_path: Path,
    requests_directory: Path,
    executions_directory: Path,
    progress: Callable[[int, int, Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Independently replay and verify one complete dynamic Qwen session."""

    root = Path(deployment_root)
    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        model = load_production_model_graph(root / "source/model_graph.v2.json")
        capability = load_production_capability(root / "capability.json")
        manifest = _canonical(root / "deployment_manifest.json", "deployment manifest")
        plan = _canonical(root / "physical/physical_plan.json", "physical plan")
        session = _canonical(Path(session_path), "dynamic session")
        aggregate = _canonical(
            Path(session_execution_path), "dynamic session execution"
        )
    except (
        CheckpointError,
        OSError,
        ProductionCapabilityError,
        ProductionModelGraphError,
    ) as exc:
        raise QwenFullModelReferenceError(
            f"cannot admit dynamic reference inputs: {exc}"
        ) from exc
    for value, field, label in (
        (manifest, "build_id", "deployment manifest"),
        (plan, "physical_plan_id", "physical plan"),
        (session, "session_id", "dynamic session"),
        (aggregate, "session_execution_id", "dynamic session execution"),
    ):
        _identity(value, field, label)

    _exact(
        session,
        {
            "build_id",
            "checkpoint_lock_id",
            "claim_boundary",
            "command_program_sha256",
            "context_capacity",
            "generation",
            "graph_id",
            "model_id",
            "prompt",
            "schema",
            "session_id",
            "session_version",
            "tokenizer",
        },
        set(),
        "dynamic session",
    )
    prompt = session.get("prompt")
    generation = session.get("generation")
    if not isinstance(prompt, dict) or not isinstance(generation, dict):
        raise QwenFullModelReferenceError(
            "independent dynamic session workload differs"
        )
    prompt_ids = prompt.get("token_ids")
    eos_ids = generation.get("eos_token_ids")
    generated_limit = generation.get("generated_token_limit")
    if (
        session.get("schema") != DYNAMIC_SESSION_SCHEMA
        or session.get("session_version")
        != "tensor-accelerator-qwen-dynamic-session-0.2.0"
        or session.get("model_id") != MODEL_ID
        or session.get("graph_id") != model.graph_id
        or session.get("build_id") != manifest.get("build_id")
        or session.get("checkpoint_lock_id") != lock["lock_id"]
        or session.get("command_program_sha256")
        != plan.get("command_program", {}).get("sha256")
        or session.get("context_capacity") != CONTEXT_CAPACITY
        or session.get("claim_boundary")
        != {
            "exact_8000_token_acceptance": False,
            "short_generation": True,
            "timing_or_performance": False,
        }
        or not isinstance(prompt.get("text"), str)
        or not prompt["text"]
        or not isinstance(prompt_ids, list)
        or not prompt_ids
        or prompt.get("token_count") != len(prompt_ids)
        or prompt.get("utf8_sha256")
        != hashlib.sha256(prompt["text"].encode()).hexdigest()
        or any(
            isinstance(token, bool)
            or not isinstance(token, int)
            or not 0 <= token < VOCABULARY_SIZE
            for token in prompt_ids
        )
        or not isinstance(eos_ids, list)
        or not eos_ids
        or len(set(eos_ids)) != len(eos_ids)
        or any(
            isinstance(token, bool)
            or not isinstance(token, int)
            or not 0 <= token < VOCABULARY_SIZE
            for token in eos_ids
        )
        or isinstance(generated_limit, bool)
        or not isinstance(generated_limit, int)
        or not 32 <= generated_limit <= CONTEXT_CAPACITY
        or len(prompt_ids) + generated_limit - 1 > CONTEXT_CAPACITY
        or generation.get("selection") != "greedy_lowest_token_id_argmax"
        or generation.get("unexpected_early_eos") != "fail"
        or plan.get("graph_id") != model.graph_id
        or plan.get("capability_id") != capability.capability_id
        or manifest.get("graph_id") != model.graph_id
        or manifest.get("capability_id") != capability.capability_id
        or manifest.get("physical_plan_id") != plan.get("physical_plan_id")
    ):
        raise QwenFullModelReferenceError(
            "independent dynamic session or deployment boundary differs"
        )

    tokenizer = _load_dynamic_tokenizer(Path(snapshot), lock, session)
    if tokenizer.decode(prompt_ids, skip_special_tokens=False) != prompt["text"]:
        raise QwenFullModelReferenceError(
            "independent dynamic prompt tokenizer round trip differs"
        )
    rope_table, rope_record = _load_rope_table(root, plan)
    transaction_count = len(prompt_ids) + generated_limit - 1
    states: dict[str, KVSnapshotReference] = {
        f"kv.layer.{layer}": empty_kv_snapshot(
            f"kv.layer.{layer}", capacity=CONTEXT_CAPACITY
        )
        for layer in range(LAYER_COUNT)
    }
    previous_report: dict[str, Any] | None = None
    previous_output_token: int | None = None
    generated_tokens: list[int] = []
    expected_steps: list[dict[str, Any]] = []
    reference_steps: list[dict[str, Any]] = []
    aggregate_counters: Counter[str] = Counter()
    for step in range(transaction_count):
        request_path = Path(requests_directory) / f"request.{step:04d}.json"
        report_path = Path(executions_directory) / f"execution.{step:04d}.json"
        request = _canonical(request_path, f"dynamic request {step}")
        report = _canonical(report_path, f"dynamic execution report {step}")
        prompt_input = step < len(prompt_ids)
        generated_index = (
            None if step < len(prompt_ids) - 1 else step - len(prompt_ids) + 1
        )
        expected_token = prompt_ids[step] if prompt_input else previous_output_token
        expected_previous = (
            None if previous_report is None else previous_report["report_id"]
        )
        if (
            expected_token is None
            or request.get("previous_report_id") != expected_previous
            or request.get("token_id") != expected_token
            or request.get("step_index") != step
            or request.get("transaction_id") != _dynamic_transaction_id(request)
            or report.get("previous_report_id") != expected_previous
        ):
            raise QwenFullModelReferenceError(
                f"independent dynamic causal chain differs at step {step}"
            )
        states_before = states
        transaction_reference, states = _check_qwen_full_model_transaction(
            snapshot=Path(snapshot),
            checkpoint_lock_path=Path(checkpoint_lock_path),
            model_graph_path=root / "source/model_graph.v2.json",
            capability_path=root / "capability.json",
            request_path=request_path,
            execution_report_path=report_path,
            dynamic_session=session,
            initial_states=states_before,
            rope_coefficients=rope_table[step],
        )
        _check_runtime_binding(report, request, plan, states_before, states)
        output_token = report["outputs"]["committed_logits"]["greedy_token_id"]
        if generated_index is not None:
            generated_tokens.append(output_token)
            if output_token in eos_ids:
                raise QwenFullModelReferenceError(
                    f"independent dynamic session observed unexpected EOS at step {step}"
                )
        aggregate_counters.update(report["counters"])
        report_payload = canonical_json_bytes(report)
        binding = report["runtime_binding"]
        state = report["state"][0]
        expected_steps.append(
            {
                "generated_token_index": generated_index,
                "input_role": "prompt" if prompt_input else "generated",
                "input_token_id": expected_token,
                "logits_sha256": report["outputs"]["committed_logits"][
                    "payload_sha256"
                ],
                "output_role": (
                    "prefill_intermediate"
                    if generated_index is None
                    else "generated_token"
                ),
                "output_token_id": output_token,
                "phase": "prefill" if prompt_input else "decode",
                "previous_report_id": expected_previous,
                "report_id": report["report_id"],
                "report_sha256": hashlib.sha256(report_payload).hexdigest(),
                "report_size_bytes": len(report_payload),
                "request_id": request["request_id"],
                "state_generation": state["generation"],
                "state_length": state["length"],
                "state_metadata_after_sha256": binding["state_metadata_after_sha256"],
                "state_metadata_before_sha256": binding["state_metadata_before_sha256"],
                "step_index": step,
            }
        )
        reference_steps.append(
            {
                "counter_sha256": transaction_reference["counter_sha256"],
                "execution_report_id": report["report_id"],
                "greedy_maximum_count": report["outputs"]["committed_logits"][
                    "greedy_maximum_count"
                ],
                "hidden_36_sha256": report["outputs"]["hidden_36"]["payload_sha256"],
                "logits_sha256": report["outputs"]["committed_logits"][
                    "payload_sha256"
                ],
                "output_token_id": output_token,
                "request_id": request["request_id"],
                "saturation_total": report["saturation"]["total"],
                "state_generation": state["generation"],
                "state_length": state["length"],
                "step_index": step,
                "transaction_reference_id": transaction_reference[
                    "transaction_reference_id"
                ],
            }
        )
        previous_report = report
        previous_output_token = output_token
        if progress is not None:
            progress(step + 1, transaction_count, reference_steps[-1])

    counters = dict(sorted(aggregate_counters.items()))
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=False)
    full_text = tokenizer.decode(
        [*prompt_ids, *generated_tokens], skip_special_tokens=False
    )
    if (
        aggregate.get("schema") != DYNAMIC_SESSION_EXECUTION_SCHEMA
        or aggregate.get("status") != "pass"
        or aggregate.get("mode") != "artifact_only_data_bearing_short_generation"
        or aggregate.get("session_id") != session["session_id"]
        or aggregate.get("build_id") != manifest["build_id"]
        or aggregate.get("graph_id") != model.graph_id
        or aggregate.get("command_program_sha256") != plan["command_program"]["sha256"]
        or aggregate.get("claim_boundary")
        != {
            "artifact_only_short_generation_complete": True,
            "exact_8000_token_acceptance": False,
            "target_precision_reference_verified": False,
            "timing_or_performance": False,
        }
        or aggregate.get("prompt_token_count") != len(prompt_ids)
        or aggregate.get("prompt_token_ids") != prompt_ids
        or aggregate.get("generated_token_count") != generated_limit
        or aggregate.get("generated_token_ids") != generated_tokens
        or aggregate.get("transaction_count") != transaction_count
        or aggregate.get("decode_transaction_count") != generated_limit - 1
        or aggregate.get("eos_observed") is not False
        or aggregate.get("tokenizer") != session["tokenizer"]
        or aggregate.get("decoded")
        != {
            "full_text": full_text,
            "generated_text": generated_text,
            "prompt_text": prompt["text"],
        }
        or aggregate.get("steps") != expected_steps
        or aggregate.get("step_chain_sha256")
        != sha256_bytes(canonical_json_bytes(expected_steps))
        or aggregate.get("aggregate_counters") != counters
        or aggregate.get("aggregate_counter_sha256")
        != sha256_bytes(canonical_json_bytes(counters))
        or previous_report is None
        or aggregate.get("final_state") != previous_report["state"]
    ):
        raise QwenFullModelReferenceError(
            "independent dynamic aggregate execution differs"
        )

    counts = {
        "checkpoint_tensor_authentications": transaction_count * WEIGHT_COUNT,
        "checkpoint_tensors_per_transaction": WEIGHT_COUNT,
        "counter_comparisons": transaction_count * 70,
        "counters_per_transaction": 70,
        "decode_transactions": generated_limit - 1,
        "generated_token_decisions": generated_limit,
        "layer_boundary_comparisons": transaction_count * LAYER_COUNT,
        "operation_comparisons": transaction_count * OPERATION_COUNT,
        "operations_per_transaction": OPERATION_COUNT,
        "rope_rows": transaction_count,
        "state_resources_per_transaction": STATE_COUNT,
        "state_transition_comparisons": transaction_count * STATE_COUNT,
        "transactions": transaction_count,
    }
    body = {
        "aggregate_counter_sha256": aggregate["aggregate_counter_sha256"],
        "build_id": manifest["build_id"],
        "capability_id": capability.capability_id,
        "checkpoint_lock_id": lock["lock_id"],
        "checks": {
            "all_checkpoint_tensors_authenticated_per_transaction": True,
            "all_counters_independently_derived": True,
            "all_layer_boundaries_exact": True,
            "all_operation_outputs_exact": True,
            "all_runtime_bindings_independently_derived": True,
            "all_state_transitions_exact": True,
            "complete_logits_ties_and_tokens_exact": True,
            "decoded_text_exact": True,
            "independent_scalar_kernel_cross_checks": True,
            "row_major_checkpoint_not_tiled_hbm_weight_source": True,
            "segmented_k_not_fused_matrix_execution": True,
            "stateful_causal_chain_exact": True,
        },
        "claim_boundary": {
            "artifact_only_short_generation_verified": True,
            "exact_8000_token_acceptance": False,
            "simulator_report_mutated": False,
            "timing_or_performance": False,
        },
        "counts": counts,
        "decoded": aggregate["decoded"],
        "final_state": aggregate["final_state"],
        "generated_token_ids": generated_tokens,
        "graph_id": model.graph_id,
        "hbm_logical_sha256": plan["hbm"]["image"]["logical_sha256"],
        "physical_plan_id": plan["physical_plan_id"],
        "reference_version": DYNAMIC_REFERENCE_VERSION,
        "rope_coefficients": {
            **rope_record,
            "qualified_rows_replayed": transaction_count,
        },
        "schema": DYNAMIC_SESSION_REFERENCE_SCHEMA,
        "session_execution_id": aggregate["session_execution_id"],
        "session_id": session["session_id"],
        "status": "pass",
        "step_reference_chain_sha256": sha256_bytes(
            canonical_json_bytes(reference_steps)
        ),
        "steps": reference_steps,
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


def publish_qwen_dynamic_session_reference(
    report: Mapping[str, Any], output: Path
) -> None:
    """Publish one canonical independent dynamic-session result without overwrite."""

    value = dict(report)
    if (
        value.get("schema") != DYNAMIC_SESSION_REFERENCE_SCHEMA
        or value.get("status") != "pass"
        or value.get("claim_boundary")
        != {
            "artifact_only_short_generation_verified": True,
            "exact_8000_token_acceptance": False,
            "simulator_report_mutated": False,
            "timing_or_performance": False,
        }
    ):
        raise QwenFullModelReferenceError("dynamic session reference boundary differs")
    _identity(value, "reference_id", "dynamic session reference")
    path = Path(output)
    if path.exists():
        raise QwenFullModelReferenceError(
            f"dynamic session reference already exists: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


__all__ = [
    "DYNAMIC_REFERENCE_VERSION",
    "DYNAMIC_SESSION_REFERENCE_SCHEMA",
    "QwenFullModelReferenceError",
    "REFERENCE_SCHEMA",
    "REFERENCE_VERSION",
    "check_qwen_dynamic_session_execution",
    "check_qwen_full_model_execution",
    "publish_qwen_dynamic_session_reference",
    "publish_qwen_full_model_reference",
]
