"""Strict semantic IR for the first executable OpenTallas vertical slice.

The current schema intentionally accepts only an exact-integer fixture profile
and two fully specified operations.  Unsupported semantics fail closed instead
of becoming zero-cost generic operations.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Any


SCHEMA = "opentallas.semantic_ir.v1"
NUMERIC_PROFILE = "int_exact_fixture_v1"
SUPPORTED_OPERATIONS = ("ROM_MATMUL", "VECTOR_ADD")
ALLOWED_STORAGE = frozenset({"input", "rom", "activation", "output"})
DTYPE_BYTES = {"i8": 1, "i32": 4}
DTYPE_RANGES = {
    "i8": (-128, 127),
    "i32": (-(1 << 31), (1 << 31) - 1),
}
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")


class IRValidationError(ValueError):
    """Raised when semantic IR is ambiguous, incomplete, or unsupported."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IRValidationError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> dict[str, Any]:
    """Load one JSON object while rejecting duplicate keys and non-finite data."""

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                IRValidationError(f"non-finite JSON number {token!r}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IRValidationError(f"cannot read strict JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise IRValidationError(f"expected a JSON object in {path}")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize deterministic JSON with no host or wall-clock state."""

    try:
        text = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise IRValidationError(f"value is not canonical JSON: {exc}") from exc
    return (text + "\n").encode("ascii")


def write_canonical_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_json_bytes(value))


def _exact_keys(value: dict[str, Any], required: set[str], optional: set[str], label: str) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - required - optional)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing {missing}")
        if unknown:
            details.append(f"unknown {unknown}")
        raise IRValidationError(f"{label} has " + "; ".join(details))


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise IRValidationError(f"{label} must be a stable identifier")
    return value


def _shape(value: Any, label: str) -> tuple[int, ...]:
    if not isinstance(value, list) or not value or len(value) > 8:
        raise IRValidationError(f"{label} must be a rank-1 through rank-8 array")
    result: list[int] = []
    elements = 1
    for index, extent in enumerate(value):
        if isinstance(extent, bool) or not isinstance(extent, int) or extent <= 0:
            raise IRValidationError(f"{label}[{index}] must be a positive integer")
        elements *= extent
        if elements > (1 << 40):
            raise IRValidationError(f"{label} element count overflows the v1 bound")
        result.append(extent)
    return tuple(result)


def _integer_values(value: Any, tensor_id: str, dtype: str, count: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != count:
        raise IRValidationError(
            f"tensor {tensor_id!r} must contain exactly {count} flattened values"
        )
    lower, upper = DTYPE_RANGES[dtype]
    result: list[int] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, int):
            raise IRValidationError(
                f"tensor {tensor_id!r} value {index} must be an integer"
            )
        if item < lower or item > upper:
            raise IRValidationError(
                f"tensor {tensor_id!r} value {index} is outside {dtype}"
            )
        result.append(item)
    return tuple(result)


@dataclass(frozen=True)
class Tensor:
    index: int
    tensor_id: str
    dtype: str
    shape: tuple[int, ...]
    storage: str
    values: tuple[int, ...] | None = None

    @property
    def element_count(self) -> int:
        return math.prod(self.shape)

    @property
    def size_bytes(self) -> int:
        return self.element_count * DTYPE_BYTES[self.dtype]

    def to_dict(self, *, include_values: bool) -> dict[str, Any]:
        result: dict[str, Any] = {
            "dtype": self.dtype,
            "id": self.tensor_id,
            "shape": list(self.shape),
            "storage": self.storage,
        }
        if include_values and self.values is not None:
            result["values"] = list(self.values)
        return result


@dataclass(frozen=True)
class Operation:
    index: int
    operation_id: str
    kind: str
    inputs: tuple[str, ...]
    output: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.operation_id,
            "inputs": list(self.inputs),
            "kind": self.kind,
            "output": self.output,
        }


@dataclass(frozen=True)
class Model:
    model_id: str
    numeric_profile: str
    tensors: tuple[Tensor, ...]
    operations: tuple[Operation, ...]
    outputs: tuple[str, ...]

    @property
    def tensor_by_id(self) -> dict[str, Tensor]:
        return {tensor.tensor_id: tensor for tensor in self.tensors}

    def to_dict(self, *, include_values: bool) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "numeric_profile": self.numeric_profile,
            "operations": [operation.to_dict() for operation in self.operations],
            "outputs": list(self.outputs),
            "schema": SCHEMA,
            "tensors": [
                tensor.to_dict(include_values=include_values) for tensor in self.tensors
            ],
        }


def _parse_tensors(values: Any, *, require_rom_values: bool) -> tuple[Tensor, ...]:
    if not isinstance(values, list) or not values:
        raise IRValidationError("tensors must be a non-empty array")
    tensors: list[Tensor] = []
    seen: set[str] = set()
    for index, raw in enumerate(values):
        if not isinstance(raw, dict):
            raise IRValidationError(f"tensor {index} must be an object")
        _exact_keys(
            raw,
            {"id", "dtype", "shape", "storage"},
            {"values"},
            f"tensor {index}",
        )
        tensor_id = _identifier(raw["id"], f"tensor {index}.id")
        if tensor_id in seen:
            raise IRValidationError(f"duplicate tensor id {tensor_id!r}")
        seen.add(tensor_id)
        dtype = raw["dtype"]
        if dtype not in DTYPE_BYTES:
            raise IRValidationError(f"tensor {tensor_id!r} has unsupported dtype {dtype!r}")
        storage = raw["storage"]
        if storage not in ALLOWED_STORAGE:
            raise IRValidationError(
                f"tensor {tensor_id!r} has unsupported storage {storage!r}"
            )
        shape = _shape(raw["shape"], f"tensor {tensor_id}.shape")
        count = math.prod(shape)
        raw_values = raw.get("values")
        if storage == "rom":
            if require_rom_values and raw_values is None:
                raise IRValidationError(f"ROM tensor {tensor_id!r} lacks payload values")
            values_parsed = (
                None
                if raw_values is None
                else _integer_values(raw_values, tensor_id, dtype, count)
            )
        else:
            if raw_values is not None:
                raise IRValidationError(
                    f"non-ROM tensor {tensor_id!r} must not embed payload values"
                )
            values_parsed = None
        tensors.append(
            Tensor(index, tensor_id, dtype, shape, storage, values_parsed)
        )
    return tuple(tensors)


def _parse_operations(values: Any) -> tuple[Operation, ...]:
    if not isinstance(values, list) or not values:
        raise IRValidationError("operations must be a non-empty array")
    operations: list[Operation] = []
    seen: set[str] = set()
    for index, raw in enumerate(values):
        if not isinstance(raw, dict):
            raise IRValidationError(f"operation {index} must be an object")
        _exact_keys(
            raw,
            {"id", "kind", "inputs", "output"},
            set(),
            f"operation {index}",
        )
        operation_id = _identifier(raw["id"], f"operation {index}.id")
        if operation_id in seen:
            raise IRValidationError(f"duplicate operation id {operation_id!r}")
        seen.add(operation_id)
        kind = raw["kind"]
        if kind not in SUPPORTED_OPERATIONS:
            raise IRValidationError(
                f"operation {operation_id!r} has unsupported kind {kind!r}"
            )
        raw_inputs = raw["inputs"]
        if not isinstance(raw_inputs, list) or len(raw_inputs) != 2:
            raise IRValidationError(
                f"operation {operation_id!r} requires exactly two explicit inputs"
            )
        inputs = tuple(
            _identifier(item, f"operation {operation_id}.inputs[{item_index}]")
            for item_index, item in enumerate(raw_inputs)
        )
        output = _identifier(raw["output"], f"operation {operation_id}.output")
        operations.append(Operation(index, operation_id, kind, inputs, output))
    return tuple(operations)


def _validate_operation_shapes(model: Model) -> None:
    tensors = model.tensor_by_id
    available = {
        tensor.tensor_id
        for tensor in model.tensors
        if tensor.storage in {"input", "rom"}
    }
    produced: set[str] = set()
    consumed: set[str] = set()
    for operation in model.operations:
        for tensor_id in operation.inputs:
            if tensor_id not in tensors:
                raise IRValidationError(
                    f"operation {operation.operation_id!r} references unknown input {tensor_id!r}"
                )
            if tensor_id not in available:
                raise IRValidationError(
                    f"operation {operation.operation_id!r} reads {tensor_id!r} before production"
                )
            consumed.add(tensor_id)
        if operation.output not in tensors:
            raise IRValidationError(
                f"operation {operation.operation_id!r} references unknown output {operation.output!r}"
            )
        output = tensors[operation.output]
        if output.storage not in {"activation", "output"}:
            raise IRValidationError(
                f"operation {operation.operation_id!r} cannot write {output.storage} tensor {output.tensor_id!r}"
            )
        if operation.output in produced or operation.output in available:
            raise IRValidationError(f"tensor {operation.output!r} has multiple producers")

        left = tensors[operation.inputs[0]]
        right = tensors[operation.inputs[1]]
        if operation.kind == "ROM_MATMUL":
            if (
                left.dtype != "i8"
                or right.dtype != "i8"
                or output.dtype != "i32"
                or len(left.shape) != 2
                or len(right.shape) != 2
                or len(output.shape) != 2
                or right.storage != "rom"
            ):
                raise IRValidationError(
                    f"ROM_MATMUL {operation.operation_id!r} requires rank-2 i8 input, rank-2 i8 ROM weight, and rank-2 i32 output"
                )
            batch, reduction = left.shape
            rows, weight_reduction = right.shape
            if weight_reduction != reduction or output.shape != (batch, rows):
                raise IRValidationError(
                    f"ROM_MATMUL {operation.operation_id!r} has incompatible explicit shapes"
                )
        elif operation.kind == "VECTOR_ADD":
            if (
                left.dtype != "i32"
                or right.dtype != "i32"
                or output.dtype != "i32"
            ):
                raise IRValidationError(
                    f"VECTOR_ADD {operation.operation_id!r} requires identical i32 dtypes"
                )
            if left.shape != right.shape or output.shape != left.shape:
                raise IRValidationError(
                    f"VECTOR_ADD {operation.operation_id!r} forbids implicit broadcasting"
                )

        produced.add(operation.output)
        available.add(operation.output)

    required_produced = {
        tensor.tensor_id
        for tensor in model.tensors
        if tensor.storage in {"activation", "output"}
    }
    if produced != required_produced:
        missing = sorted(required_produced - produced)
        extra = sorted(produced - required_produced)
        raise IRValidationError(
            f"produced tensor coverage mismatch: missing={missing}, extra={extra}"
        )
    required_outputs = tuple(
        tensor.tensor_id for tensor in model.tensors if tensor.storage == "output"
    )
    if model.outputs != required_outputs:
        raise IRValidationError(
            "outputs must list every output-storage tensor once in declaration order"
        )
    if len(model.outputs) != 1:
        raise IRValidationError("microcode ABI v1 requires exactly one declared output")
    unused_sources = sorted(
        tensor.tensor_id
        for tensor in model.tensors
        if tensor.storage in {"input", "rom"} and tensor.tensor_id not in consumed
    )
    if unused_sources:
        raise IRValidationError(f"source tensors have no execution role: {unused_sources}")


def parse_model(value: dict[str, Any], *, require_rom_values: bool = True) -> Model:
    _exact_keys(
        value,
        {"schema", "model_id", "numeric_profile", "tensors", "operations", "outputs"},
        set(),
        "semantic IR",
    )
    if value["schema"] != SCHEMA:
        raise IRValidationError(f"unsupported semantic IR schema {value['schema']!r}")
    model_id = _identifier(value["model_id"], "model_id")
    if value["numeric_profile"] != NUMERIC_PROFILE:
        raise IRValidationError(
            f"unsupported numeric profile {value['numeric_profile']!r}; only the fixture profile is implemented"
        )
    tensors = _parse_tensors(value["tensors"], require_rom_values=require_rom_values)
    operations = _parse_operations(value["operations"])
    raw_outputs = value["outputs"]
    if not isinstance(raw_outputs, list) or not raw_outputs:
        raise IRValidationError("outputs must be a non-empty array")
    outputs = tuple(
        _identifier(item, f"outputs[{index}]") for index, item in enumerate(raw_outputs)
    )
    if len(set(outputs)) != len(outputs):
        raise IRValidationError("outputs contains a duplicate tensor")
    model = Model(model_id, value["numeric_profile"], tensors, operations, outputs)
    _validate_operation_shapes(model)
    return model


def load_model(path: Path, *, require_rom_values: bool = True) -> Model:
    return parse_model(load_strict_json(path), require_rom_values=require_rom_values)
