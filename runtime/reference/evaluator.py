"""Independent exact-integer reference for the compiler fixture.

This module intentionally does not import compiler lowering, image, microcode,
or service-engine code. It evaluates source semantic operations directly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ReferenceError(RuntimeError):
    """Raised when source semantics or reference inputs are invalid."""


def _duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReferenceError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_duplicates
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReferenceError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReferenceError(f"expected object in {path}")
    return value


def _canonical_sha256(value: Any) -> str:
    payload = (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _checked_i32(value: int, label: str) -> int:
    if value < -(1 << 31) or value > (1 << 31) - 1:
        raise ReferenceError(f"signed i32 overflow during {label}")
    return value


def _shape_elements(shape: Any, label: str) -> int:
    if not isinstance(shape, list) or not shape:
        raise ReferenceError(f"{label} has no explicit shape")
    result = 1
    for extent in shape:
        if isinstance(extent, bool) or not isinstance(extent, int) or extent <= 0:
            raise ReferenceError(f"{label} has an invalid extent")
        result *= extent
    return result


def _dtype_range(dtype: Any, label: str) -> tuple[int, int]:
    if dtype == "i8":
        return -128, 127
    if dtype == "i32":
        return -(1 << 31), (1 << 31) - 1
    raise ReferenceError(f"{label} has unsupported dtype {dtype!r}")


def _integer_payload(
    values: Any, *, count: int, dtype: Any, label: str
) -> tuple[int, ...]:
    if not isinstance(values, list) or len(values) != count:
        raise ReferenceError(f"{label} payload length differs from its shape")
    lower, upper = _dtype_range(dtype, label)
    parsed: list[int] = []
    for index, value in enumerate(values):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < lower
            or value > upper
        ):
            raise ReferenceError(f"{label} value {index} is outside {dtype}")
        parsed.append(value)
    return tuple(parsed)


def evaluate_reference(source_ir: Path, request_path: Path) -> dict[str, Any]:
    source = _load(source_ir)
    request = _load(request_path)
    if set(source) != {
        "model_id",
        "numeric_profile",
        "operations",
        "outputs",
        "schema",
        "tensors",
    }:
        raise ReferenceError("reference source IR has missing or unknown fields")
    if set(request) != {"model_id", "schema", "tensors"}:
        raise ReferenceError("reference request has missing or unknown fields")
    if (
        source.get("schema") != "opentallas.semantic_ir.v1"
        or source.get("numeric_profile") != "int_exact_fixture_v1"
    ):
        raise ReferenceError("reference supports only semantic IR fixture v1")
    model_id = source.get("model_id")
    if (
        request.get("schema") != "opentallas.execution_request.v1"
        or request.get("model_id") != model_id
    ):
        raise ReferenceError("reference request identity differs from source IR")

    raw_tensors = source.get("tensors")
    if not isinstance(raw_tensors, list):
        raise ReferenceError("source tensors are missing")
    metadata: dict[str, dict[str, Any]] = {}
    state: dict[str, tuple[int, ...]] = {}
    for raw in raw_tensors:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
            raise ReferenceError("source tensor record is malformed")
        tensor_id = raw["id"]
        if tensor_id in metadata:
            raise ReferenceError(f"duplicate tensor {tensor_id!r}")
        storage = raw.get("storage")
        if storage not in {"input", "rom", "activation", "output"}:
            raise ReferenceError(f"tensor {tensor_id!r} has unsupported storage")
        allowed_fields = {"dtype", "id", "shape", "storage"}
        if storage == "rom":
            allowed_fields.add("values")
        if set(raw) != allowed_fields:
            raise ReferenceError(
                f"tensor {tensor_id!r} has missing or unknown fields"
            )
        count = _shape_elements(raw.get("shape"), f"tensor {tensor_id!r}")
        _dtype_range(raw.get("dtype"), f"tensor {tensor_id!r}")
        metadata[tensor_id] = raw
        if storage == "rom":
            state[tensor_id] = _integer_payload(
                raw.get("values"),
                count=count,
                dtype=raw.get("dtype"),
                label=f"ROM tensor {tensor_id!r}",
            )

    request_records = request.get("tensors")
    if not isinstance(request_records, list):
        raise ReferenceError("reference input tensor table is missing")
    for raw in request_records:
        if (
            not isinstance(raw, dict)
            or set(raw) != {"dtype", "id", "shape", "values"}
            or raw.get("id") not in metadata
        ):
            raise ReferenceError("reference input tensor is unknown")
        tensor_id = raw["id"]
        tensor = metadata[tensor_id]
        if tensor.get("storage") != "input" or tensor_id in state:
            raise ReferenceError(f"reference input {tensor_id!r} is duplicated or illegal")
        if raw.get("dtype") != tensor.get("dtype") or raw.get("shape") != tensor.get("shape"):
            raise ReferenceError(f"reference input metadata differs for {tensor_id!r}")
        state[tensor_id] = _integer_payload(
            raw.get("values"),
            count=_shape_elements(tensor["shape"], f"input {tensor_id!r}"),
            dtype=tensor["dtype"],
            label=f"reference input {tensor_id!r}",
        )

    expected_inputs = {
        tensor_id
        for tensor_id, tensor in metadata.items()
        if tensor.get("storage") == "input"
    }
    if not expected_inputs.issubset(state):
        raise ReferenceError("reference request does not cover every model input")
    operations = source.get("operations")
    if not isinstance(operations, list):
        raise ReferenceError("source operations are missing")
    for raw in operations:
        if not isinstance(raw, dict) or set(raw) != {"id", "inputs", "kind", "output"}:
            raise ReferenceError("source operation is malformed")
        inputs = raw.get("inputs")
        output = raw.get("output")
        if (
            not isinstance(inputs, list)
            or len(inputs) != 2
            or not isinstance(output, str)
            or output not in metadata
            or inputs[0] not in state
            or inputs[1] not in state
            or output in state
        ):
            raise ReferenceError("source operation dataflow is invalid")
        left = state[inputs[0]]
        right = state[inputs[1]]
        if raw.get("kind") == "ROM_MATMUL":
            left_shape = metadata[inputs[0]]["shape"]
            right_shape = metadata[inputs[1]]["shape"]
            output_shape = metadata[output]["shape"]
            if (
                metadata[inputs[0]]["dtype"] != "i8"
                or metadata[inputs[1]]["dtype"] != "i8"
                or metadata[inputs[1]]["storage"] != "rom"
                or metadata[output]["dtype"] != "i32"
                or len(left_shape) != 2
                or len(right_shape) != 2
            ):
                raise ReferenceError("reference ROM_MATMUL metadata is unsupported")
            batch, reduction = left_shape
            rows, right_reduction = right_shape
            if reduction != right_reduction or output_shape != [batch, rows]:
                raise ReferenceError("reference matmul shapes differ")
            result: list[int] = []
            for batch_index in range(batch):
                for row_index in range(rows):
                    accumulator = 0
                    for reduction_index in range(reduction):
                        accumulator = _checked_i32(
                            accumulator
                            + left[batch_index * reduction + reduction_index]
                            * right[row_index * reduction + reduction_index],
                            "reference ROM_MATMUL",
                        )
                    result.append(accumulator)
            state[output] = tuple(result)
        elif raw.get("kind") == "VECTOR_ADD":
            if (
                metadata[inputs[0]]["dtype"] != "i32"
                or metadata[inputs[1]]["dtype"] != "i32"
                or metadata[output]["dtype"] != "i32"
                or metadata[inputs[0]]["shape"] != metadata[inputs[1]]["shape"]
                or metadata[output]["shape"] != metadata[inputs[0]]["shape"]
                or len(left) != len(right)
            ):
                raise ReferenceError("reference VECTOR_ADD shapes differ")
            state[output] = tuple(
                _checked_i32(a + b, "reference VECTOR_ADD")
                for a, b in zip(left, right, strict=True)
            )
        else:
            raise ReferenceError(f"reference operation {raw.get('kind')!r} is unsupported")

    outputs_raw = source.get("outputs")
    if not isinstance(outputs_raw, list) or not outputs_raw:
        raise ReferenceError("source output list is missing")
    outputs = []
    for tensor_id in outputs_raw:
        if tensor_id not in state:
            raise ReferenceError(f"reference output {tensor_id!r} is unavailable")
        tensor = metadata[tensor_id]
        outputs.append(
            {
                "dtype": tensor["dtype"],
                "id": tensor_id,
                "shape": tensor["shape"],
                "values": list(state[tensor_id]),
            }
        )
    return {
        "model_id": model_id,
        "outputs": outputs,
        "request_sha256": _canonical_sha256(request),
        "schema": "opentallas.reference_result.v1",
        "semantic_sha256": _canonical_sha256(source),
        "status": "pass",
    }
