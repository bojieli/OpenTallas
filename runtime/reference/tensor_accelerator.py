"""Independent exact-integer oracle for the tensor-accelerator fixture.

This module deliberately imports no compiler, command, physical-plan, simulator,
or target-kernel implementation. It evaluates the source Model Graph directly.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any


class TensorAcceleratorReferenceError(RuntimeError):
    """Raised when source semantics or reference inputs are invalid."""


def _duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TensorAcceleratorReferenceError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _nonfinite(token: str) -> None:
    raise TensorAcceleratorReferenceError(f"non-finite JSON number {token!r}")


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_duplicates,
            parse_constant=_nonfinite,
        )
    except TensorAcceleratorReferenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TensorAcceleratorReferenceError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TensorAcceleratorReferenceError(f"expected object in {path}")
    return value


def _canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise TensorAcceleratorReferenceError(
            f"value cannot be canonicalized: {exc}"
        ) from exc
    return (text + "\n").encode("ascii")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _checked_i32(value: int, label: str) -> int:
    if value < -(1 << 31) or value > (1 << 31) - 1:
        raise TensorAcceleratorReferenceError(
            f"signed i32 overflow during {label}"
        )
    return value


def _shape(raw: Any, symbols: dict[str, int], label: str) -> tuple[int, ...]:
    if not isinstance(raw, list) or not raw:
        raise TensorAcceleratorReferenceError(f"{label} lacks a shape")
    result: list[int] = []
    for dimension in raw:
        if isinstance(dimension, bool):
            raise TensorAcceleratorReferenceError(f"{label} has an invalid dimension")
        if isinstance(dimension, int) and dimension > 0:
            result.append(dimension)
        elif isinstance(dimension, str) and dimension in symbols:
            result.append(symbols[dimension])
        else:
            raise TensorAcceleratorReferenceError(
                f"{label} has an unknown or invalid dimension"
            )
    return tuple(result)


def _integer_values(
    raw: Any,
    *,
    count: int,
    dtype: Any,
    label: str,
) -> tuple[int, ...]:
    if dtype == "i8":
        lower, upper = -128, 127
    elif dtype == "i32":
        lower, upper = -(1 << 31), (1 << 31) - 1
    else:
        raise TensorAcceleratorReferenceError(
            f"{label} has unsupported dtype {dtype!r}"
        )
    if not isinstance(raw, list) or len(raw) != count:
        raise TensorAcceleratorReferenceError(
            f"{label} payload length differs from its shape"
        )
    result: list[int] = []
    for index, value in enumerate(raw):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < lower
            or value > upper
        ):
            raise TensorAcceleratorReferenceError(
                f"{label} value {index} is outside {dtype}"
            )
        result.append(value)
    return tuple(result)


def _payload_sha256(dtype: str, values: tuple[int, ...]) -> str:
    try:
        if dtype == "i8":
            payload = struct.pack(f"<{len(values)}b", *values)
        elif dtype == "i32":
            payload = struct.pack(f"<{len(values)}i", *values)
        else:
            raise TensorAcceleratorReferenceError(
                f"cannot encode reference dtype {dtype!r}"
            )
    except struct.error as exc:
        raise TensorAcceleratorReferenceError(
            f"cannot encode reference output: {exc}"
        ) from exc
    return _sha256(payload)


def _parse_symbols(model: dict[str, Any], request: dict[str, Any]) -> dict[str, int]:
    raw_symbols = model.get("symbols")
    request_symbols = request.get("symbols")
    if not isinstance(raw_symbols, list) or not isinstance(request_symbols, dict):
        raise TensorAcceleratorReferenceError("symbol records are malformed")
    symbols: dict[str, int] = {}
    for raw in raw_symbols:
        if (
            not isinstance(raw, dict)
            or set(raw)
            != {"default", "id", "maximum", "minimum", "multiple_of"}
            or not isinstance(raw.get("id"), str)
            or raw["id"] in symbols
        ):
            raise TensorAcceleratorReferenceError("source symbol is malformed")
        symbol_id = raw["id"]
        if symbol_id not in request_symbols:
            raise TensorAcceleratorReferenceError(
                f"request lacks symbol {symbol_id!r}"
            )
        value = request_symbols[symbol_id]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < raw["minimum"]
            or value > raw["maximum"]
            or value % raw["multiple_of"]
            or value != raw["default"]
        ):
            raise TensorAcceleratorReferenceError(
                f"request symbol {symbol_id!r} is outside the qualified value"
            )
        symbols[symbol_id] = value
    if set(request_symbols) != set(symbols):
        raise TensorAcceleratorReferenceError("request symbols differ from the graph")
    return symbols


def evaluate_tensor_accelerator_reference(
    model_path: Path,
    request_path: Path,
) -> dict[str, Any]:
    """Evaluate the qualified source graph without compiler artifacts."""

    model = _load(model_path)
    request = _load(request_path)
    if set(model) != {
        "model_id",
        "numeric_profile",
        "operations",
        "outputs",
        "schema",
        "symbols",
        "tensors",
    }:
        raise TensorAcceleratorReferenceError(
            "source Model Graph has missing or unknown fields"
        )
    if (
        model.get("schema") != "opentallas.model_graph.v1"
        or model.get("numeric_profile") != "int_exact_tensor_accelerator_v1"
    ):
        raise TensorAcceleratorReferenceError(
            "reference supports only the exact-integer tensor-accelerator profile"
        )
    if set(request) != {"model_id", "schema", "symbols", "tensors"}:
        raise TensorAcceleratorReferenceError("request has missing or unknown fields")
    if (
        request.get("schema")
        != "opentallas.tensor_accelerator.execution_request.v1"
        or request.get("model_id") != model.get("model_id")
    ):
        raise TensorAcceleratorReferenceError(
            "request identity differs from the source graph"
        )
    symbols = _parse_symbols(model, request)

    raw_tensors = model.get("tensors")
    if not isinstance(raw_tensors, list):
        raise TensorAcceleratorReferenceError("source tensors are malformed")
    metadata: dict[str, dict[str, Any]] = {}
    shapes: dict[str, tuple[int, ...]] = {}
    state: dict[str, tuple[int, ...]] = {}
    for raw in raw_tensors:
        if (
            not isinstance(raw, dict)
            or not isinstance(raw.get("id"), str)
            or raw["id"] in metadata
        ):
            raise TensorAcceleratorReferenceError("source tensor is malformed")
        tensor_id = raw["id"]
        role = raw.get("role")
        expected_keys = {"dtype", "id", "layout", "role", "shape"}
        if role in {"weight", "constant"}:
            expected_keys.add("values")
        if set(raw) != expected_keys:
            raise TensorAcceleratorReferenceError(
                f"tensor {tensor_id!r} has missing or unknown fields"
            )
        shape = _shape(raw["shape"], symbols, f"tensor {tensor_id!r}")
        metadata[tensor_id] = raw
        shapes[tensor_id] = shape
        if role in {"weight", "constant"}:
            state[tensor_id] = _integer_values(
                raw["values"],
                count=math.prod(shape),
                dtype=raw["dtype"],
                label=f"initializer {tensor_id!r}",
            )

    request_tensors = request.get("tensors")
    if not isinstance(request_tensors, list):
        raise TensorAcceleratorReferenceError("request tensors are malformed")
    for raw in request_tensors:
        if (
            not isinstance(raw, dict)
            or set(raw) != {"dtype", "id", "shape", "values"}
            or raw.get("id") not in metadata
        ):
            raise TensorAcceleratorReferenceError("request tensor is unknown")
        tensor_id = raw["id"]
        tensor = metadata[tensor_id]
        if (
            tensor.get("role") != "input"
            or tensor_id in state
            or raw["dtype"] != tensor["dtype"]
            or raw["shape"] != list(shapes[tensor_id])
        ):
            raise TensorAcceleratorReferenceError(
                f"request tensor {tensor_id!r} differs or is duplicated"
            )
        state[tensor_id] = _integer_values(
            raw["values"],
            count=math.prod(shapes[tensor_id]),
            dtype=tensor["dtype"],
            label=f"input {tensor_id!r}",
        )
    expected_inputs = {
        tensor_id
        for tensor_id, tensor in metadata.items()
        if tensor.get("role") == "input"
    }
    if not expected_inputs.issubset(state):
        raise TensorAcceleratorReferenceError("request lacks model inputs")

    operations = model.get("operations")
    if not isinstance(operations, list):
        raise TensorAcceleratorReferenceError("source operations are malformed")
    for raw in operations:
        if (
            not isinstance(raw, dict)
            or set(raw)
            != {"attributes", "id", "inputs", "kind", "numeric", "outputs"}
        ):
            raise TensorAcceleratorReferenceError("source operation is malformed")
        inputs = raw["inputs"]
        outputs = raw["outputs"]
        if (
            not isinstance(inputs, list)
            or len(inputs) != 2
            or not isinstance(outputs, list)
            or len(outputs) != 1
            or any(tensor_id not in state for tensor_id in inputs)
            or outputs[0] not in metadata
            or outputs[0] in state
        ):
            raise TensorAcceleratorReferenceError("source dataflow is invalid")
        left = state[inputs[0]]
        right = state[inputs[1]]
        output_id = outputs[0]
        if raw["kind"] == "MATMUL":
            m, k = shapes[inputs[0]]
            n, weight_k = shapes[inputs[1]]
            if (
                weight_k != k
                or shapes[output_id] != (m, n)
                or metadata[inputs[0]]["dtype"] != "i8"
                or metadata[inputs[1]]["dtype"] != "i8"
                or metadata[output_id]["dtype"] != "i32"
                or raw["numeric"]
                != {
                    "accumulator_dtype": "i32",
                    "input_dtype": "i8",
                    "output_dtype": "i32",
                    "reduction_order": "ascending_k",
                    "weight_dtype": "i8",
                }
            ):
                raise TensorAcceleratorReferenceError(
                    "reference MATMUL contract is unsupported"
                )
            result: list[int] = []
            for row_m in range(m):
                for row_n in range(n):
                    accumulator = 0
                    for reduction in range(k):
                        accumulator = _checked_i32(
                            accumulator
                            + left[row_m * k + reduction]
                            * right[row_n * k + reduction],
                            "reference MATMUL",
                        )
                    result.append(accumulator)
            state[output_id] = tuple(result)
        elif raw["kind"] == "ADD":
            if (
                shapes[inputs[0]] != shapes[inputs[1]]
                or shapes[output_id] != shapes[inputs[0]]
                or metadata[inputs[0]]["dtype"] != "i32"
                or metadata[inputs[1]]["dtype"] != "i32"
                or metadata[output_id]["dtype"] != "i32"
                or raw["numeric"] != {"dtype": "i32", "rounding": "exact"}
            ):
                raise TensorAcceleratorReferenceError(
                    "reference ADD contract is unsupported"
                )
            state[output_id] = tuple(
                _checked_i32(left_value + right_value, "reference ADD")
                for left_value, right_value in zip(left, right, strict=True)
            )
        else:
            raise TensorAcceleratorReferenceError(
                f"reference operation {raw['kind']!r} is unsupported"
            )

    raw_outputs = model.get("outputs")
    if not isinstance(raw_outputs, list) or not raw_outputs:
        raise TensorAcceleratorReferenceError("source outputs are missing")
    outputs: list[dict[str, Any]] = []
    for tensor_id in raw_outputs:
        if tensor_id not in state:
            raise TensorAcceleratorReferenceError(
                f"output {tensor_id!r} is unavailable"
            )
        tensor = metadata[tensor_id]
        values = state[tensor_id]
        outputs.append(
            {
                "dtype": tensor["dtype"],
                "id": tensor_id,
                "payload_sha256": _payload_sha256(tensor["dtype"], values),
                "shape": list(shapes[tensor_id]),
                "values": list(values),
            }
        )
    return {
        "model_id": model["model_id"],
        "outputs": outputs,
        "request_sha256": _sha256(_canonical_bytes(request)),
        "schema": "opentallas.tensor_accelerator.reference_result.v1",
        "semantic_sha256": _sha256(_canonical_bytes(model)),
        "status": "pass",
    }
