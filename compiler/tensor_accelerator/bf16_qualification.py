"""Reproducible real-payload qualification for the BF16 matrix contract."""

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
from runtime.tensor_accelerator.bf16 import (
    BF16KernelError,
    dense_bf16_linear_bf16 as execute_full_matrix,
)

from .common import (
    ArtifactError,
    canonical_json_bytes,
    require_int,
    require_sha256,
    sha256_bytes,
)


SCHEMA = "opentallas.tensor_accelerator.bf16_projection_qualification.v1"
NUMERIC_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"
MAX_WEIGHT_BYTES = 1 << 32


class BF16QualificationError(ArtifactError):
    """Raised when payload evidence or differential execution fails."""


def _record(raw: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise BF16QualificationError(f"{label} must be a tensor record")
    dtype = raw.get("dtype")
    name = raw.get("name")
    shape = raw.get("shape")
    size_bytes = raw.get("size_bytes")
    if (
        dtype != "BF16"
        or not isinstance(name, str)
        or not name
        or not isinstance(shape, list)
        or len(shape) != 2
    ):
        raise BF16QualificationError(f"{label} must be a rank-2 BF16 tensor")
    parsed_shape = [
        require_int(value, f"{label}.shape[{index}]", minimum=1, maximum=1 << 30)
        for index, value in enumerate(shape)
    ]
    expected_size = 2 * parsed_shape[0] * parsed_shape[1]
    if size_bytes != expected_size:
        raise BF16QualificationError(f"{label} byte size differs from shape")
    return {
        "dtype": "BF16",
        "name": name,
        "payload_sha256": require_sha256(
            raw.get("payload_sha256"), f"{label}.payload_sha256"
        ),
        "shape": parsed_shape,
        "size_bytes": expected_size,
    }


def _indices(raw: Sequence[int], output_rows: int) -> tuple[int, ...]:
    if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
        raise BF16QualificationError("selected_rows must be a sequence")
    result = tuple(
        require_int(
            value,
            f"selected_rows[{index}]",
            minimum=0,
            maximum=output_rows - 1,
        )
        for index, value in enumerate(raw)
    )
    if not result or result != tuple(sorted(set(result))):
        raise BF16QualificationError(
            "selected_rows must be nonempty, unique, and strictly increasing"
        )
    return result


def _codes(payload: bytes, shape: tuple[int, int], label: str) -> np.ndarray:
    expected = 2 * shape[0] * shape[1]
    if not isinstance(payload, bytes) or len(payload) != expected:
        raise BF16QualificationError(f"{label} payload byte count differs")
    return np.frombuffer(payload, dtype="<u2").reshape(shape)


def qualify_bf16_projection_payloads(
    *,
    checkpoint_lock_id: str,
    input_record: Mapping[str, Any],
    input_row: int,
    input_row_payload: bytes,
    weight_record: Mapping[str, Any],
    weight_payload: bytes,
    selected_rows: Sequence[int],
) -> dict[str, Any]:
    """Execute and independently check one full-dimension BF16 projection."""

    lock_id = require_sha256(checkpoint_lock_id, "checkpoint_lock_id")
    input_metadata = _record(input_record, "input_record")
    weight_metadata = _record(weight_record, "weight_record")
    row = require_int(
        input_row,
        "input_row",
        minimum=0,
        maximum=input_metadata["shape"][0] - 1,
    )
    reduction = input_metadata["shape"][1]
    if weight_metadata["shape"][1] != reduction:
        raise BF16QualificationError("input and weight reduction widths differ")
    if weight_metadata["size_bytes"] > MAX_WEIGHT_BYTES:
        raise BF16QualificationError("weight exceeds the qualification memory bound")
    if len(input_row_payload) != 2 * reduction:
        raise BF16QualificationError("input row payload byte count differs")
    if hashlib.sha256(weight_payload).hexdigest() != weight_metadata["payload_sha256"]:
        raise BF16QualificationError("weight payload differs from its tensor record")
    indices = _indices(selected_rows, weight_metadata["shape"][0])
    inputs = _codes(input_row_payload, (1, reduction), "input row")
    weights = _codes(
        weight_payload,
        tuple(weight_metadata["shape"]),
        "weight",
    )

    try:
        executed = execute_full_matrix(
            inputs,
            weights,
            input_tile_rows=1,
            output_tile_rows=64,
        )
        reference = reference_selected_rows(
            inputs.tolist(),
            weights[list(indices)].tolist(),
            output_row_indices=indices,
            declared_output_count=weight_metadata["shape"][0],
        )
    except (BF16KernelError, BF16MatrixReferenceError) as exc:
        raise BF16QualificationError(f"BF16 projection execution failed: {exc}") from exc
    observed = tuple(int(executed.values[0, index]) for index in indices)
    if observed != reference.values[0]:
        raise BF16QualificationError(
            "optimized projection differs from the independent selected-row reference"
        )
    output_payload = executed.values.astype("<u2", copy=False).tobytes(order="C")
    body: dict[str, Any] = {
        "accounting": {
            "accumulation_additions": (
                weight_metadata["shape"][0] * reduction
            ),
            "input_payload_bytes": len(input_row_payload),
            "scalar_multiplications": weight_metadata["shape"][0] * reduction,
            "weight_payload_bytes": len(weight_payload),
        },
        "checkpoint_lock_id": lock_id,
        "input": {
            "row": row,
            "row_payload_sha256": hashlib.sha256(input_row_payload).hexdigest(),
            "source_payload_sha256": input_metadata["payload_sha256"],
            "source_shape": input_metadata["shape"],
            "tensor": input_metadata["name"],
        },
        "numeric_contract": NUMERIC_CONTRACT,
        "output": {
            "payload_sha256": hashlib.sha256(output_payload).hexdigest(),
            "saturated_element_count": executed.output_saturated_element_count,
            "shape": list(executed.values.shape),
        },
        "schema": SCHEMA,
        "selected_reference": {
            "output_codes": list(observed),
            "output_rows": list(indices),
            "saturated_element_count": reference.output_saturated_element_count,
            "status": "exact_match",
        },
        "status": "pass",
        "weight": {
            "payload_sha256": weight_metadata["payload_sha256"],
            "shape": weight_metadata["shape"],
            "tensor": weight_metadata["name"],
        },
    }
    return {
        **body,
        "report_id": sha256_bytes(canonical_json_bytes(body)),
    }


def _authenticated_row_consumer(
    *,
    row_start: int,
    row_bytes: int,
) -> tuple[bytearray, Any]:
    captured = bytearray()
    cursor = 0

    def consume(chunk: bytes) -> None:
        nonlocal cursor
        chunk_end = cursor + len(chunk)
        overlap_start = max(cursor, row_start)
        overlap_end = min(chunk_end, row_start + row_bytes)
        if overlap_start < overlap_end:
            captured.extend(
                chunk[overlap_start - cursor : overlap_end - cursor]
            )
        cursor = chunk_end

    return captured, consume


def qualify_locked_bf16_projection(
    *,
    snapshot: Path,
    checkpoint_lock_path: Path,
    input_tensor: str,
    input_row: int,
    weight_tensor: str,
    selected_rows: Sequence[int],
) -> dict[str, Any]:
    """Stream-authenticate locked tensors and run projection qualification."""

    try:
        lock = load_checkpoint_lock(Path(checkpoint_lock_path))
        with LockedCheckpointReader(Path(snapshot), lock) as reader:
            raw_input = reader.tensor_record(input_tensor)
            input_metadata = _record(raw_input, "locked input tensor")
            row = require_int(
                input_row,
                "input_row",
                minimum=0,
                maximum=input_metadata["shape"][0] - 1,
            )
            row_bytes = input_metadata["shape"][1] * 2
            captured, consumer = _authenticated_row_consumer(
                row_start=row * row_bytes,
                row_bytes=row_bytes,
            )
            reader.consume_tensor_payload(input_tensor, consumer)
            weight_payload = bytearray()
            raw_weight = reader.consume_tensor_payload(
                weight_tensor, weight_payload.extend
            )
    except (CheckpointError, ArtifactError) as exc:
        raise BF16QualificationError(f"locked checkpoint read failed: {exc}") from exc
    if len(captured) != row_bytes:
        raise BF16QualificationError("authenticated input row extraction is incomplete")
    return qualify_bf16_projection_payloads(
        checkpoint_lock_id=lock["lock_id"],
        input_record=raw_input,
        input_row=row,
        input_row_payload=bytes(captured),
        weight_record=raw_weight,
        weight_payload=bytes(weight_payload),
        selected_rows=selected_rows,
    )


def publish_qualification_report(report: Mapping[str, Any], output_path: Path) -> None:
    """Atomically publish a canonical report without overwriting evidence."""

    if not isinstance(report, Mapping):
        raise BF16QualificationError("qualification report must be an object")
    body = {key: value for key, value in report.items() if key != "report_id"}
    if (
        report.get("schema") != SCHEMA
        or report.get("status") != "pass"
        or report.get("report_id") != sha256_bytes(canonical_json_bytes(body))
    ):
        raise BF16QualificationError("qualification report identity or status differs")
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
            raise BF16QualificationError(
                f"report already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "BF16QualificationError",
    "NUMERIC_CONTRACT",
    "SCHEMA",
    "publish_qualification_report",
    "qualify_bf16_projection_payloads",
    "qualify_locked_bf16_projection",
]
