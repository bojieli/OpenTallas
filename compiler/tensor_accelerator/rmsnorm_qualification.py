"""Real-checkpoint qualification for Qwen embedding-to-RMSNorm execution."""

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
from runtime.reference.tensor_accelerator_rmsnorm import (
    EPSILON_CODE,
    NUMERIC_CONTRACT,
    RMSNormReferenceError,
    rms_norm_bf16 as reference_rmsnorm,
)
from runtime.tensor_accelerator.rmsnorm import (
    RMSNormKernelError,
    rms_norm_bf16 as execute_rmsnorm,
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


SCHEMA = "opentallas.tensor_accelerator.rmsnorm_qualification.v1"
MAX_WIDTH = 1 << 20
MAX_REFERENCE_ELEMENTS = 1 << 20


class RMSNormQualificationError(ArtifactError):
    """Raised when real payload qualification cannot be proven exactly."""


def _record(
    raw: Mapping[str, Any],
    label: str,
    *,
    expected_rank: int,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise RMSNormQualificationError(f"{label} must be a tensor record")
    dtype = raw.get("dtype")
    name = raw.get("name")
    shape = raw.get("shape")
    size_bytes = raw.get("size_bytes")
    if (
        dtype != "BF16"
        or not isinstance(name, str)
        or not name
        or not isinstance(shape, list)
        or len(shape) != expected_rank
    ):
        raise RMSNormQualificationError(
            f"{label} must be a rank-{expected_rank} BF16 tensor"
        )
    parsed_shape = [
        require_int(value, f"{label}.shape[{index}]", minimum=1, maximum=1 << 30)
        for index, value in enumerate(shape)
    ]
    elements = 1
    for extent in parsed_shape:
        elements *= extent
    expected_size = 2 * elements
    if size_bytes != expected_size:
        raise RMSNormQualificationError(f"{label} byte size differs from shape")
    return {
        "dtype": "BF16",
        "name": name,
        "payload_sha256": require_sha256(
            raw.get("payload_sha256"), f"{label}.payload_sha256"
        ),
        "shape": parsed_shape,
        "size_bytes": expected_size,
    }


def _indices(raw: Sequence[int], width: int) -> tuple[int, ...]:
    if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
        raise RMSNormQualificationError("selected_elements must be a sequence")
    result = tuple(
        require_int(
            value,
            f"selected_elements[{position}]",
            minimum=0,
            maximum=width - 1,
        )
        for position, value in enumerate(raw)
    )
    if not result or result != tuple(sorted(set(result))):
        raise RMSNormQualificationError(
            "selected_elements must be nonempty, unique, and strictly increasing"
        )
    return result


def _capture_row(total_shape: tuple[int, int], row: int) -> tuple[bytearray, Any]:
    row_bytes = total_shape[1] * 2
    start = row * row_bytes
    captured = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        end = cursor + len(chunk)
        overlap_start = max(cursor, start)
        overlap_end = min(end, start + row_bytes)
        if overlap_start < overlap_end:
            captured.extend(chunk[overlap_start - cursor : overlap_end - cursor])
        cursor = end

    return captured, consume


def qualify_rmsnorm_payloads(
    *,
    checkpoint_lock_id: str,
    embedding_record: Mapping[str, Any],
    token_id: int,
    embedding_payload: bytes,
    weight_record: Mapping[str, Any],
    weight_payload: bytes,
    selected_elements: Sequence[int],
) -> dict[str, Any]:
    """Execute and independently check one full-width embedding RMSNorm."""

    lock_id = require_sha256(checkpoint_lock_id, "checkpoint_lock_id")
    embedding = _record(embedding_record, "embedding_record", expected_rank=2)
    weight = _record(weight_record, "weight_record", expected_rank=1)
    row = require_int(
        token_id,
        "token_id",
        minimum=0,
        maximum=embedding["shape"][0] - 1,
    )
    width = embedding["shape"][1]
    if width > MAX_WIDTH or weight["shape"] != [width]:
        raise RMSNormQualificationError(
            "RMSNorm weight width differs from the embedding hidden width"
        )
    if width > MAX_REFERENCE_ELEMENTS:
        raise RMSNormQualificationError("RMSNorm exceeds scalar reference bound")
    if len(embedding_payload) != 2 * width:
        raise RMSNormQualificationError("embedding row payload byte count differs")
    if len(weight_payload) != 2 * width:
        raise RMSNormQualificationError("weight payload byte count differs")
    if hashlib.sha256(weight_payload).hexdigest() != weight["payload_sha256"]:
        raise RMSNormQualificationError("weight payload differs from its record")
    indices = _indices(selected_elements, width)
    inputs = np.frombuffer(embedding_payload, dtype="<u2").reshape(1, width)
    weights = np.frombuffer(weight_payload, dtype="<u2")
    try:
        executed = execute_rmsnorm(inputs, weights)
        reference = reference_rmsnorm(inputs.tolist(), weights.tolist())
    except (RMSNormKernelError, RMSNormReferenceError) as exc:
        raise RMSNormQualificationError(f"RMSNorm execution failed: {exc}") from exc
    executed_values = tuple(int(value) for value in executed.values[0].tolist())
    executed_normalized = tuple(
        int(value) for value in executed.normalized_values[0].tolist()
    )
    if (
        executed_values != reference.values[0]
        or executed_normalized != reference.normalized_values[0]
        or tuple(int(value) for value in executed.mean_square_codes.tolist())
        != reference.mean_square_codes
        or tuple(int(value) for value in executed.inverse_rms_codes.tolist())
        != reference.inverse_rms_codes
        or executed.normalized_saturated_element_count
        != reference.normalized_saturated_element_count
        or executed.output_saturated_element_count
        != reference.output_saturated_element_count
    ):
        raise RMSNormQualificationError(
            "optimized RMSNorm differs from the independent scalar reference"
        )
    normalized_payload = executed.normalized_values.astype(
        "<u2", copy=False
    ).tobytes(order="C")
    output_payload = executed.values.astype("<u2", copy=False).tobytes(order="C")
    body: dict[str, Any] = {
        "accounting": {
            "epsilon_additions": 1,
            "final_weight_multiplications": width,
            "input_square_multiplications": width,
            "mean_divisions": 1,
            "normalization_multiplications": width,
            "reduction_additions": width - 1,
            "reciprocal_square_roots": 1,
        },
        "checkpoint_lock_id": lock_id,
        "epsilon_binary32_code": EPSILON_CODE,
        "input": {
            "row_payload_sha256": hashlib.sha256(embedding_payload).hexdigest(),
            "source_payload_sha256": embedding["payload_sha256"],
            "source_shape": embedding["shape"],
            "tensor": embedding["name"],
            "token_id": row,
        },
        "numeric_contract": NUMERIC_CONTRACT,
        "output": {
            "inverse_rms_binary32_code": reference.inverse_rms_codes[0],
            "mean_square_binary32_code": reference.mean_square_codes[0],
            "normalized_payload_sha256": hashlib.sha256(
                normalized_payload
            ).hexdigest(),
            "normalized_saturated_element_count": (
                reference.normalized_saturated_element_count
            ),
            "payload_sha256": hashlib.sha256(output_payload).hexdigest(),
            "saturated_element_count": reference.output_saturated_element_count,
            "shape": [1, width],
        },
        "schema": SCHEMA,
        "selected_reference": {
            "element_indices": list(indices),
            "normalized_codes": [executed_normalized[index] for index in indices],
            "output_codes": [executed_values[index] for index in indices],
            "status": "exact_match",
        },
        "status": "pass",
        "weight": {
            "payload_sha256": weight["payload_sha256"],
            "shape": weight["shape"],
            "tensor": weight["name"],
        },
    }
    return {**body, "report_id": sha256_bytes(canonical_json_bytes(body))}


def qualify_locked_rmsnorm(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    embedding_tensor: str,
    token_id: int,
    weight_tensor: str,
    selected_elements: Sequence[int],
) -> dict[str, Any]:
    """Authenticate locked payloads and produce real-checkpoint evidence."""

    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        with LockedCheckpointReader(Path(snapshot), lock) as reader:
            raw_embedding = reader.tensor_record(embedding_tensor)
            embedding = _record(
                raw_embedding, "locked embedding tensor", expected_rank=2
            )
            row = require_int(
                token_id,
                "token_id",
                minimum=0,
                maximum=embedding["shape"][0] - 1,
            )
            captured, consumer = _capture_row(tuple(embedding["shape"]), row)
            reader.consume_tensor_payload(embedding_tensor, consumer)
            weight_payload = bytearray()
            raw_weight = reader.consume_tensor_payload(
                weight_tensor, weight_payload.extend
            )
    except (CheckpointError, ArtifactError) as exc:
        raise RMSNormQualificationError(
            f"locked checkpoint qualification failed: {exc}"
        ) from exc
    return qualify_rmsnorm_payloads(
        checkpoint_lock_id=lock["lock_id"],
        embedding_record=raw_embedding,
        token_id=row,
        embedding_payload=bytes(captured),
        weight_record=raw_weight,
        weight_payload=bytes(weight_payload),
        selected_elements=selected_elements,
    )


def load_rmsnorm_qualification(path: Path) -> dict[str, Any]:
    """Load a canonical qualification report and validate its identity."""

    try:
        payload = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise RMSNormQualificationError(
            f"cannot load RMSNorm qualification report: {exc}"
        ) from exc
    if payload != canonical_json_bytes(value):
        raise RMSNormQualificationError("RMSNorm qualification is not canonical JSON")
    exact_keys(
        value,
        {
            "accounting",
            "checkpoint_lock_id",
            "epsilon_binary32_code",
            "input",
            "numeric_contract",
            "output",
            "report_id",
            "schema",
            "selected_reference",
            "status",
            "weight",
        },
        set(),
        "RMSNorm qualification",
    )
    if value["schema"] != SCHEMA or value["status"] != "pass":
        raise RMSNormQualificationError("RMSNorm qualification status/schema differs")
    observed = require_sha256(value["report_id"], "report_id")
    expected = sha256_bytes(
        canonical_json_bytes(
            {key: item for key, item in value.items() if key != "report_id"}
        )
    )
    if observed != expected:
        raise RMSNormQualificationError("RMSNorm qualification report_id differs")
    if (
        value["numeric_contract"] != NUMERIC_CONTRACT
        or value["epsilon_binary32_code"] != EPSILON_CODE
    ):
        raise RMSNormQualificationError("RMSNorm numeric contract differs")
    return value


def publish_rmsnorm_qualification(
    report: Mapping[str, Any], output_path: Path
) -> None:
    """Atomically retain canonical qualification evidence without overwrite."""

    if not isinstance(report, Mapping):
        raise RMSNormQualificationError("qualification report must be an object")
    body = {key: value for key, value in report.items() if key != "report_id"}
    if (
        report.get("schema") != SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise RMSNormQualificationError(
            "qualification report identity or status differs"
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
            raise RMSNormQualificationError(
                f"report already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "RMSNormQualificationError",
    "SCHEMA",
    "load_rmsnorm_qualification",
    "publish_rmsnorm_qualification",
    "qualify_locked_rmsnorm",
    "qualify_rmsnorm_payloads",
]
