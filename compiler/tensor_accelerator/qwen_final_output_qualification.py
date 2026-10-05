"""Actual-checkpoint qualification for the Qwen final-output operator family."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np

from compiler.frontend.checkpoint import (
    CheckpointError,
    LockedCheckpointReader,
    load_checkpoint_lock,
)
from runtime.reference.tensor_accelerator_bf16 import (
    BF16MatrixReferenceError,
    dense_bf16_linear_selected_rows_bf16 as reference_selected_rows,
)
from runtime.reference.tensor_accelerator_rmsnorm import (
    RMSNormReferenceError,
    rms_norm_bf16 as reference_rmsnorm,
)
from runtime.reference.tensor_accelerator_selection import (
    SelectionReferenceError,
    last_token_select_bf16 as reference_select,
)
from runtime.tensor_accelerator.bf16 import (
    BF16KernelError,
    dense_bf16_linear_bf16,
)
from runtime.tensor_accelerator.rmsnorm import (
    EPSILON_CODE,
    RMSNormKernelError,
    rms_norm_bf16,
)
from runtime.tensor_accelerator.selection import (
    SelectionKernelError,
    last_token_select_bf16,
)

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)
from .production_model import (
    ProductionModelGraph,
    ProductionModelGraphError,
    ProductionOperation,
    ProductionTensor,
    load_production_model_graph,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_final_output_qualification.v1"
CONNECTED_EXECUTION_SCHEMA = (
    "opentallas.tensor_accelerator.connected_layer_execution.v1"
)
MODEL_ID = "qwen3-8b"
HIDDEN_WIDTH = 4096
VOCABULARY_SIZE = 151936
RMSNORM_CONTRACT = "qwen3_rmsnorm_fp32_bf16_v1"
SELECTION_CONTRACT = "exact_index_select_v1"
MATRIX_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"
FINAL_OPERATION_IDS = ("node.0613", "node.0614", "node.0615")
TOP_LEVEL_KEYS = {
    "accounting",
    "checkpoint_lock_id",
    "connected_input",
    "graph_id",
    "input",
    "numeric_contracts",
    "operations",
    "outputs",
    "projection_saturated_element_count",
    "report_id",
    "rmsnorm",
    "schema",
    "selected_reference",
    "sources",
    "status",
    "target_adaptation",
}


class QwenFinalOutputQualificationError(ArtifactError):
    """Raised when final-output evidence is incomplete or inconsistent."""


def _identity(value: Mapping[str, Any], field: str, label: str) -> None:
    observed = require_sha256(value.get(field), f"{label}.{field}")
    expected = sha256_bytes(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    )
    if observed != expected:
        raise QwenFinalOutputQualificationError(f"{label} identity differs")


def _load_canonical(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise QwenFinalOutputQualificationError(f"cannot load {label}: {exc}") from exc
    if payload != canonical_json_bytes(value):
        raise QwenFinalOutputQualificationError(f"{label} is not canonical JSON")
    return value, payload


def _payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def _u32_payload(values: np.ndarray) -> bytes:
    return np.ascontiguousarray(values, dtype="<u4").tobytes(order="C")


def _hash(values: np.ndarray) -> str:
    return hashlib.sha256(_payload(values)).hexdigest()


def _finite_codes(payload: bytes, shape: Sequence[int], label: str) -> np.ndarray:
    elements = 1
    for extent in shape:
        elements *= extent
    if len(payload) != 2 * elements:
        raise QwenFinalOutputQualificationError(
            f"{label} payload byte count differs from shape"
        )
    values = np.frombuffer(payload, dtype="<u2").reshape(tuple(shape))
    if np.any((values & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise QwenFinalOutputQualificationError(f"{label} contains nonfinite BF16")
    return values


def _connected_hidden(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    value, payload = _load_canonical(path, "connected-layer execution report")
    if (
        value.get("schema") != CONNECTED_EXECUTION_SCHEMA
        or value.get("status") != "pass"
        or value.get("mode") != "artifact_only_data_bearing_functional"
    ):
        raise QwenFinalOutputQualificationError(
            "connected-layer execution status or mode differs"
        )
    _identity(value, "report_id", "connected-layer execution report")
    output = value.get("output")
    if not isinstance(output, dict) or set(output) != {"hidden_1"}:
        raise QwenFinalOutputQualificationError(
            "connected-layer output coverage differs"
        )
    hidden = output["hidden_1"]
    if (
        not isinstance(hidden, dict)
        or hidden.get("dtype") != "bf16"
        or hidden.get("shape") != [1, HIDDEN_WIDTH]
        or not isinstance(hidden.get("codes"), list)
        or len(hidden["codes"]) != HIDDEN_WIDTH
    ):
        raise QwenFinalOutputQualificationError(
            "connected-layer hidden output contract differs"
        )
    codes = np.asarray(
        [
            require_int(code, f"hidden_1.codes[{index}]", minimum=0, maximum=0xFFFF)
            for index, code in enumerate(hidden["codes"])
        ],
        dtype=np.uint16,
    ).reshape(1, HIDDEN_WIDTH)
    digest = _hash(codes)
    if digest != require_sha256(
        hidden.get("payload_sha256"), "hidden_1.payload_sha256"
    ):
        raise QwenFinalOutputQualificationError(
            "connected-layer hidden payload identity differs"
        )
    return codes, {
        "build_id": require_sha256(value.get("build_id"), "connected build_id"),
        "hidden_payload_sha256": digest,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "report_id": value["report_id"],
    }


def _operation_by_id(model: ProductionModelGraph) -> dict[str, ProductionOperation]:
    return {operation.operation_id: operation for operation in model.operations}


def _validate_model(model: ProductionModelGraph) -> tuple[ProductionOperation, ...]:
    operations = _operation_by_id(model)
    if model.model_id != MODEL_ID or len(model.operations) != 617:
        raise QwenFinalOutputQualificationError("Qwen model graph coverage differs")
    try:
        selected = tuple(
            operations[operation_id] for operation_id in FINAL_OPERATION_IDS
        )
    except KeyError as exc:
        raise QwenFinalOutputQualificationError(
            "Qwen final-output operation is missing"
        ) from exc
    expected = (
        (
            "RMS_NORM",
            RMSNORM_CONTRACT,
            ("hidden.36", "model.norm.weight"),
            ("hidden.final_norm",),
        ),
        (
            "LAST_TOKEN_SELECT",
            SELECTION_CONTRACT,
            ("hidden.final_norm",),
            ("hidden.last_token",),
        ),
        (
            "MATMUL",
            MATRIX_CONTRACT,
            ("hidden.last_token", "lm_head.weight"),
            ("output.logits",),
        ),
    )
    for operation, contract in zip(selected, expected, strict=True):
        kind, numeric, inputs, outputs = contract
        if (
            operation.kind != kind
            or operation.numeric_contract != numeric
            or operation.inputs != inputs
            or operation.outputs != outputs
            or operation.phases != ("prefill", "decode")
            or operation.predicate != {"kind": "always"}
        ):
            raise QwenFinalOutputQualificationError(
                f"final operation {operation.operation_id!r} differs"
            )
    return selected


def _source_tensor(model: ProductionModelGraph, tensor_id: str) -> ProductionTensor:
    tensor = model.tensor_by_id.get(tensor_id)
    if tensor is None or tensor.binding is None:
        raise QwenFinalOutputQualificationError(
            f"source tensor {tensor_id!r} lacks a checkpoint binding"
        )
    if (
        tensor.dtype != "bf16"
        or tensor.role != "weight"
        or len(tensor.binding.sources) != 1
        or tensor.binding.sources[0].tensor_name != tensor_id
        or tensor.binding.sources[0].dtype != "bf16"
    ):
        raise QwenFinalOutputQualificationError(
            f"source tensor {tensor_id!r} binding differs"
        )
    return tensor


def _read_source(
    reader: LockedCheckpointReader,
    tensor: ProductionTensor,
) -> tuple[dict[str, Any], bytes]:
    source = tensor.binding.sources[0]
    record = reader.tensor_record(source.tensor_name)
    if (
        record["dtype"].lower() != source.dtype
        or tuple(record["shape"]) != source.shape
        or record["payload_sha256"] != source.payload_sha256
    ):
        raise QwenFinalOutputQualificationError(
            f"checkpoint record for {tensor.tensor_id!r} differs from Model Graph IR"
        )
    chunks = bytearray()
    reader.consume_tensor_payload(source.tensor_name, chunks.extend)
    payload = bytes(chunks)
    if hashlib.sha256(payload).hexdigest() != source.payload_sha256:
        raise QwenFinalOutputQualificationError(
            f"checkpoint payload for {tensor.tensor_id!r} differs"
        )
    return record, payload


def _source_record(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "payload_sha256": record["payload_sha256"],
        "shape": record["shape"],
        "size_bytes": record["size_bytes"],
        "tensor": record["name"],
    }


def _checked_rmsnorm(
    hidden: np.ndarray,
    weight: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    try:
        executed = rms_norm_bf16(hidden, weight, epsilon_code=EPSILON_CODE)
        reference = reference_rmsnorm(
            hidden.tolist(), weight.tolist(), epsilon_code=EPSILON_CODE
        )
    except (RMSNormKernelError, RMSNormReferenceError) as exc:
        raise QwenFinalOutputQualificationError(
            f"final RMSNorm qualification failed: {exc}"
        ) from exc
    values = tuple(tuple(int(item) for item in row) for row in executed.values)
    normalized = tuple(
        tuple(int(item) for item in row) for row in executed.normalized_values
    )
    if (
        values != reference.values
        or normalized != reference.normalized_values
        or tuple(int(item) for item in executed.mean_square_codes)
        != reference.mean_square_codes
        or tuple(int(item) for item in executed.inverse_rms_codes)
        != reference.inverse_rms_codes
        or executed.normalized_saturated_element_count
        != reference.normalized_saturated_element_count
        or executed.output_saturated_element_count
        != reference.output_saturated_element_count
    ):
        raise QwenFinalOutputQualificationError(
            "optimized final RMSNorm differs from scalar reference"
        )
    return executed.values, {
        "inverse_rms_binary32_codes_sha256": hashlib.sha256(
            _u32_payload(executed.inverse_rms_codes)
        ).hexdigest(),
        "mean_square_binary32_codes_sha256": hashlib.sha256(
            _u32_payload(executed.mean_square_codes)
        ).hexdigest(),
        "normalized_payload_sha256": _hash(executed.normalized_values),
        "normalized_saturated_element_count": (
            executed.normalized_saturated_element_count
        ),
        "output_saturated_element_count": executed.output_saturated_element_count,
    }


def _checked_selection(final_norm: np.ndarray) -> np.ndarray:
    fixture = np.concatenate((np.flip(final_norm, axis=1), final_norm), axis=0)
    try:
        executed = last_token_select_bf16(fixture, logical_rows=2)
        reference = reference_select(fixture.tolist(), logical_rows=2)
    except (SelectionKernelError, SelectionReferenceError) as exc:
        raise QwenFinalOutputQualificationError(
            f"last-token selection qualification failed: {exc}"
        ) from exc
    observed = tuple(tuple(int(item) for item in row) for row in executed.values)
    if (
        executed.index != 1
        or executed.index != reference.index
        or observed != reference.values
    ):
        raise QwenFinalOutputQualificationError(
            "optimized last-token selection differs from scalar reference"
        )
    return executed.values


def _checked_vocabulary_projection(
    hidden: np.ndarray,
    weight: np.ndarray,
) -> tuple[np.ndarray, int, tuple[int, ...], tuple[int, ...]]:
    try:
        executed = dense_bf16_linear_bf16(
            hidden,
            weight,
            input_tile_rows=1,
            output_tile_rows=64,
        )
    except BF16KernelError as exc:
        raise QwenFinalOutputQualificationError(
            f"vocabulary projection failed: {exc}"
        ) from exc
    values = executed.values
    decoded = np.ascontiguousarray(values.astype(np.uint32) << np.uint32(16)).view(
        np.float32
    )
    argmax = int(np.argmax(decoded[0]))
    selected_rows = tuple(
        sorted({0, 1, VOCABULARY_SIZE // 2, argmax, VOCABULARY_SIZE - 1})
    )
    try:
        reference = reference_selected_rows(
            hidden.tolist(),
            weight[list(selected_rows)].tolist(),
            output_row_indices=selected_rows,
            declared_output_count=VOCABULARY_SIZE,
        )
    except BF16MatrixReferenceError as exc:
        raise QwenFinalOutputQualificationError(
            f"vocabulary scalar reference failed: {exc}"
        ) from exc
    observed = tuple(int(values[0, index]) for index in selected_rows)
    if observed != reference.values[0]:
        raise QwenFinalOutputQualificationError(
            "optimized vocabulary projection differs from scalar reference"
        )
    return values, executed.output_saturated_element_count, selected_rows, observed


def qualify_locked_qwen_final_output(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    model_graph_path: Path,
    connected_execution_path: Path,
) -> dict[str, Any]:
    """Qualify final RMSNorm, row selection, vocabulary projection, and argmax."""

    hidden, connected = _connected_hidden(Path(connected_execution_path))
    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        model = load_production_model_graph(Path(model_graph_path))
    except (CheckpointError, ProductionModelGraphError) as exc:
        raise QwenFinalOutputQualificationError(
            f"final-output source admission failed: {exc}"
        ) from exc
    operations = _validate_model(model)
    norm_tensor = _source_tensor(model, "model.norm.weight")
    head_tensor = _source_tensor(model, "lm_head.weight")
    if (
        norm_tensor.binding.checkpoint_lock_id != lock["lock_id"]
        or head_tensor.binding.checkpoint_lock_id != lock["lock_id"]
    ):
        raise QwenFinalOutputQualificationError(
            "final-output graph bindings and checkpoint lock differ"
        )
    try:
        with LockedCheckpointReader(Path(snapshot), lock) as reader:
            norm_record, norm_payload = _read_source(reader, norm_tensor)
            head_record, head_payload = _read_source(reader, head_tensor)
    except (CheckpointError, OSError) as exc:
        raise QwenFinalOutputQualificationError(
            f"locked final-output checkpoint read failed: {exc}"
        ) from exc
    if norm_record["shape"] != [HIDDEN_WIDTH] or head_record["shape"] != [
        VOCABULARY_SIZE,
        HIDDEN_WIDTH,
    ]:
        raise QwenFinalOutputQualificationError("final-output checkpoint shapes differ")
    norm_weight = _finite_codes(norm_payload, [HIDDEN_WIDTH], "final norm weight")
    head_weight = _finite_codes(
        head_payload,
        [VOCABULARY_SIZE, HIDDEN_WIDTH],
        "vocabulary weight",
    )
    final_norm, rmsnorm = _checked_rmsnorm(hidden, norm_weight)
    last_token = _checked_selection(final_norm)
    logits, projection_saturation, selected_rows, selected_codes = (
        _checked_vocabulary_projection(last_token, head_weight)
    )
    decoded = np.ascontiguousarray(logits.astype(np.uint32) << np.uint32(16)).view(
        np.float32
    )
    argmax = int(np.argmax(decoded[0]))
    maximum = decoded[0, argmax]
    tie_count = int(np.count_nonzero(decoded[0] == maximum))
    values = {
        "final_norm": final_norm,
        "last_token": last_token,
        "logits": logits,
    }
    selected_output_indices = {
        "final_norm": (0, HIDDEN_WIDTH // 2, HIDDEN_WIDTH - 1),
        "last_token": (0, HIDDEN_WIDTH // 2, HIDDEN_WIDTH - 1),
        "logits": selected_rows,
    }
    flattened = {role: value.reshape(-1) for role, value in values.items()}
    body: dict[str, Any] = {
        "accounting": {
            "epsilon_additions": 1,
            "final_weight_multiplications": HIDDEN_WIDTH,
            "input_square_multiplications": HIDDEN_WIDTH,
            "mean_divisions": 1,
            "normalization_multiplications": HIDDEN_WIDTH,
            "projection_accumulation_additions": VOCABULARY_SIZE * HIDDEN_WIDTH,
            "projection_multiplications": VOCABULARY_SIZE * HIDDEN_WIDTH,
            "reciprocal_square_roots": 1,
            "reduction_additions": HIDDEN_WIDTH - 1,
            "selected_row_bytes": HIDDEN_WIDTH * 2,
            "vocabulary_elements": VOCABULARY_SIZE,
        },
        "checkpoint_lock_id": lock["lock_id"],
        "connected_input": connected,
        "graph_id": model.graph_id,
        "input": {
            "classification": "authentic_connected_layer_proxy",
            "payload_sha256": _hash(hidden),
            "shape": [1, HIDDEN_WIDTH],
        },
        "numeric_contracts": [
            MATRIX_CONTRACT,
            SELECTION_CONTRACT,
            RMSNORM_CONTRACT,
        ],
        "operations": [operation.operation_id for operation in operations],
        "outputs": {
            "final_norm": {
                "payload_sha256": _hash(final_norm),
                "shape": [1, HIDDEN_WIDTH],
            },
            "last_token": {
                "payload_sha256": _hash(last_token),
                "selected_index": 1,
                "shape": [1, HIDDEN_WIDTH],
            },
            "logits": {
                "argmax_tie_count": tie_count,
                "argmax_token_id": argmax,
                "payload_sha256": _hash(logits),
                "shape": [1, VOCABULARY_SIZE],
            },
        },
        "projection_saturated_element_count": projection_saturation,
        "rmsnorm": rmsnorm,
        "schema": SCHEMA,
        "selected_reference": {
            "output": {
                role: {
                    "codes": [int(flattened[role][index]) for index in indices],
                    "element_indices": list(indices),
                }
                for role, indices in selected_output_indices.items()
            },
            "projection": {
                "codes": list(selected_codes),
                "rows": list(selected_rows),
            },
            "selection_fixture_rows": 2,
            "status": "exact_match",
        },
        "sources": {
            "final_norm_weight": _source_record(norm_record),
            "vocabulary_weight": _source_record(head_record),
        },
        "status": "pass",
        "target_adaptation": {
            "classification": "qualified_operator_family_fixture",
            "framework_fallback": False,
            "full_model_claim": False,
            "input_boundary": "connected_layer_hidden_1_not_hidden_36",
            "matrix_reduction": "strictly_increasing_k_binary32_rne",
        },
    }
    return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def load_qwen_final_output_qualification(path: Path) -> dict[str, Any]:
    """Load and authenticate one retained final-output qualification."""

    value, _ = _load_canonical(Path(path), "Qwen final-output qualification")
    try:
        exact_keys(value, TOP_LEVEL_KEYS, set(), "Qwen final-output qualification")
    except ArtifactError as exc:
        raise QwenFinalOutputQualificationError(
            f"Qwen final-output qualification key set differs: {exc}"
        ) from exc
    if (
        value.get("schema") != SCHEMA
        or value.get("status") != "pass"
        or value.get("operations") != list(FINAL_OPERATION_IDS)
        or value.get("numeric_contracts")
        != [MATRIX_CONTRACT, SELECTION_CONTRACT, RMSNORM_CONTRACT]
        or value.get("target_adaptation", {}).get("full_model_claim") is not False
    ):
        raise QwenFinalOutputQualificationError(
            "Qwen final-output qualification contract differs"
        )
    _identity(value, "report_id", "Qwen final-output qualification")
    return value


def publish_qwen_final_output_qualification(
    report: Mapping[str, Any],
    output_path: Path,
) -> None:
    """Atomically retain canonical final-output evidence without overwrite."""

    if not isinstance(report, Mapping):
        raise QwenFinalOutputQualificationError(
            "Qwen final-output qualification must be an object"
        )
    body = {key: value for key, value in report.items() if key != "report_id"}
    if (
        report.get("schema") != SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise QwenFinalOutputQualificationError(
            "Qwen final-output qualification identity/status differs"
        )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(dict(report)))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise QwenFinalOutputQualificationError(
                f"qualification evidence will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "FINAL_OPERATION_IDS",
    "HIDDEN_WIDTH",
    "QwenFinalOutputQualificationError",
    "SCHEMA",
    "VOCABULARY_SIZE",
    "load_qwen_final_output_qualification",
    "publish_qwen_final_output_qualification",
    "qualify_locked_qwen_final_output",
]
