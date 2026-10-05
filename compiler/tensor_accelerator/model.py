"""Backend-neutral Model Graph IR for tensor-accelerator compilation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping

from .common import (
    ArtifactError,
    exact_keys,
    load_strict_json,
    require_identifier,
    require_int,
)


SCHEMA = "opentallas.model_graph.v1"
QUALIFIED_FIXTURE_PROFILE = "int_exact_tensor_accelerator_v1"
KNOWN_NUMERIC_PROFILES = frozenset(
    {
        QUALIFIED_FIXTURE_PROFILE,
        "qwen3_bf16_gqa_v1",
        "deepseek_v4_mixed_v1",
    }
)
KNOWN_DTYPES = frozenset(
    {
        "i8",
        "i32",
        "bf16",
        "fp32",
        "fp8_e4m3fn",
        "mxfp4_e2m1",
        "fp4_e2m1",
        "e8m0",
    }
)
DTYPE_BYTES = {
    "i8": 1,
    "i32": 4,
    "bf16": 2,
    "fp32": 4,
    "fp8_e4m3fn": 1,
    "mxfp4_e2m1": 1,
    "fp4_e2m1": 1,
    "e8m0": 1,
}
INTEGER_RANGES = {
    "i8": (-128, 127),
    "i32": (-(1 << 31), (1 << 31) - 1),
}
ROLES = frozenset({"input", "weight", "constant", "activation", "output", "state"})
LAYOUTS = frozenset({"row_major", "scalar", "opaque"})
KNOWN_OPERATION_KINDS = frozenset(
    {
        "ADD",
        "ATTENTION",
        "COMPRESS",
        "CONVERT",
        "EMBEDDING_LOOKUP",
        "EXPERT_DISPATCH",
        "EXPERT_REDUCE",
        "GATHER",
        "KV_COMMIT",
        "KV_READ",
        "LAST_TOKEN_SELECT",
        "MATMUL",
        "RMS_NORM",
        "ROPE",
        "ROUTE",
        "SILU_MUL",
        "SINKHORN",
        "SOFTMAX",
        "TOPK",
    }
)


class ModelGraphError(ArtifactError):
    """Raised when Model Graph IR is incomplete, ambiguous, or inconsistent."""


@dataclass(frozen=True)
class Symbol:
    symbol_id: str
    minimum: int
    maximum: int
    multiple_of: int
    default: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "default": self.default,
            "id": self.symbol_id,
            "maximum": self.maximum,
            "minimum": self.minimum,
            "multiple_of": self.multiple_of,
        }


Dimension = int | str


@dataclass(frozen=True)
class Tensor:
    index: int
    tensor_id: str
    dtype: str
    shape: tuple[Dimension, ...]
    role: str
    layout: str
    values: tuple[int, ...] | None

    def resolved_shape(self, symbols: Mapping[str, Symbol]) -> tuple[int, ...]:
        return tuple(
            dimension if isinstance(dimension, int) else symbols[dimension].default
            for dimension in self.shape
        )

    def element_count(self, symbols: Mapping[str, Symbol]) -> int:
        return math.prod(self.resolved_shape(symbols))

    def size_bytes(self, symbols: Mapping[str, Symbol]) -> int:
        elements = self.element_count(symbols)
        if self.dtype in {"mxfp4_e2m1", "fp4_e2m1"}:
            return (elements + 1) // 2
        return elements * DTYPE_BYTES[self.dtype]

    def to_dict(self, *, include_values: bool) -> dict[str, Any]:
        result: dict[str, Any] = {
            "dtype": self.dtype,
            "id": self.tensor_id,
            "layout": self.layout,
            "role": self.role,
            "shape": list(self.shape),
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
    outputs: tuple[str, ...]
    attributes: Mapping[str, Any]
    numeric: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attributes": dict(self.attributes),
            "id": self.operation_id,
            "inputs": list(self.inputs),
            "kind": self.kind,
            "numeric": dict(self.numeric),
            "outputs": list(self.outputs),
        }


@dataclass(frozen=True)
class ModelGraph:
    model_id: str
    numeric_profile: str
    symbols: tuple[Symbol, ...]
    tensors: tuple[Tensor, ...]
    operations: tuple[Operation, ...]
    outputs: tuple[str, ...]

    @property
    def symbol_by_id(self) -> dict[str, Symbol]:
        return {symbol.symbol_id: symbol for symbol in self.symbols}

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
            "symbols": [symbol.to_dict() for symbol in self.symbols],
            "tensors": [
                tensor.to_dict(include_values=include_values)
                for tensor in self.tensors
            ],
        }


def _parse_symbols(raw_symbols: Any) -> tuple[Symbol, ...]:
    if not isinstance(raw_symbols, list):
        raise ModelGraphError("symbols must be an array")
    result: list[Symbol] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_symbols):
        if not isinstance(raw, dict):
            raise ModelGraphError(f"symbol {index} must be an object")
        exact_keys(
            raw,
            {"id", "minimum", "maximum", "multiple_of", "default"},
            set(),
            f"symbol {index}",
        )
        symbol_id = require_identifier(raw["id"], f"symbol {index}.id")
        if symbol_id in seen:
            raise ModelGraphError(f"duplicate symbol id {symbol_id!r}")
        seen.add(symbol_id)
        minimum = require_int(raw["minimum"], f"symbol {symbol_id}.minimum", minimum=1)
        maximum = require_int(
            raw["maximum"],
            f"symbol {symbol_id}.maximum",
            minimum=minimum,
            maximum=1 << 30,
        )
        multiple = require_int(
            raw["multiple_of"],
            f"symbol {symbol_id}.multiple_of",
            minimum=1,
            maximum=maximum,
        )
        default = require_int(
            raw["default"],
            f"symbol {symbol_id}.default",
            minimum=minimum,
            maximum=maximum,
        )
        if minimum % multiple or maximum % multiple or default % multiple:
            raise ModelGraphError(
                f"symbol {symbol_id!r} bounds/default must be divisible by multiple_of"
            )
        result.append(Symbol(symbol_id, minimum, maximum, multiple, default))
    return tuple(result)


def _parse_shape(
    raw: Any,
    tensor_id: str,
    symbols: Mapping[str, Symbol],
) -> tuple[Dimension, ...]:
    if not isinstance(raw, list) or not raw or len(raw) > 8:
        raise ModelGraphError(f"tensor {tensor_id!r} shape must have rank 1 through 8")
    result: list[Dimension] = []
    maximum_elements = 1
    for index, dimension in enumerate(raw):
        if isinstance(dimension, bool):
            raise ModelGraphError(
                f"tensor {tensor_id!r} shape[{index}] is not a legal dimension"
            )
        if isinstance(dimension, int):
            parsed: Dimension = require_int(
                dimension,
                f"tensor {tensor_id}.shape[{index}]",
                minimum=1,
                maximum=1 << 30,
            )
            maximum_elements *= parsed
        elif isinstance(dimension, str) and dimension in symbols:
            parsed = dimension
            maximum_elements *= symbols[dimension].maximum
        else:
            raise ModelGraphError(
                f"tensor {tensor_id!r} shape[{index}] references an unknown symbol"
            )
        if maximum_elements > 1 << 50:
            raise ModelGraphError(f"tensor {tensor_id!r} maximum element count overflows")
        result.append(parsed)
    return tuple(result)


def _parse_values(
    raw: Any,
    tensor_id: str,
    dtype: str,
    expected_count: int,
) -> tuple[int, ...]:
    if dtype not in INTEGER_RANGES:
        raise ModelGraphError(
            f"inline values are not qualified for tensor {tensor_id!r} dtype {dtype!r}"
        )
    if not isinstance(raw, list) or len(raw) != expected_count:
        raise ModelGraphError(
            f"tensor {tensor_id!r} must contain exactly {expected_count} inline values"
        )
    lower, upper = INTEGER_RANGES[dtype]
    values: list[int] = []
    for index, value in enumerate(raw):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < lower
            or value > upper
        ):
            raise ModelGraphError(
                f"tensor {tensor_id!r} value {index} is outside {dtype}"
            )
        values.append(value)
    return tuple(values)


def _parse_tensors(
    raw_tensors: Any,
    symbols: Mapping[str, Symbol],
    *,
    require_initializers: bool,
) -> tuple[Tensor, ...]:
    if not isinstance(raw_tensors, list) or not raw_tensors:
        raise ModelGraphError("tensors must be a non-empty array")
    result: list[Tensor] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_tensors):
        if not isinstance(raw, dict):
            raise ModelGraphError(f"tensor {index} must be an object")
        exact_keys(
            raw,
            {"id", "dtype", "shape", "role", "layout"},
            {"values"},
            f"tensor {index}",
        )
        tensor_id = require_identifier(raw["id"], f"tensor {index}.id")
        if tensor_id in seen:
            raise ModelGraphError(f"duplicate tensor id {tensor_id!r}")
        seen.add(tensor_id)
        dtype = raw["dtype"]
        if dtype not in KNOWN_DTYPES:
            raise ModelGraphError(f"tensor {tensor_id!r} has unknown dtype {dtype!r}")
        role = raw["role"]
        if role not in ROLES:
            raise ModelGraphError(f"tensor {tensor_id!r} has unknown role {role!r}")
        layout = raw["layout"]
        if layout not in LAYOUTS:
            raise ModelGraphError(f"tensor {tensor_id!r} has unknown layout {layout!r}")
        shape = _parse_shape(raw["shape"], tensor_id, symbols)
        raw_values = raw.get("values")
        if role in {"weight", "constant"}:
            if require_initializers and raw_values is None:
                raise ModelGraphError(f"tensor {tensor_id!r} lacks initializer values")
            values = (
                None
                if raw_values is None
                else _parse_values(
                    raw_values,
                    tensor_id,
                    dtype,
                    math.prod(
                        dimension
                        if isinstance(dimension, int)
                        else symbols[dimension].default
                        for dimension in shape
                    ),
                )
            )
        else:
            if raw_values is not None:
                raise ModelGraphError(
                    f"non-initializer tensor {tensor_id!r} must not contain values"
                )
            values = None
        result.append(Tensor(index, tensor_id, dtype, shape, role, layout, values))
    return tuple(result)


def _mapping(raw: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(raw, dict):
        raise ModelGraphError(f"{label} must be an object")
    return raw


def _parse_operations(raw_operations: Any) -> tuple[Operation, ...]:
    if not isinstance(raw_operations, list) or not raw_operations:
        raise ModelGraphError("operations must be a non-empty array")
    result: list[Operation] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_operations):
        if not isinstance(raw, dict):
            raise ModelGraphError(f"operation {index} must be an object")
        exact_keys(
            raw,
            {"id", "kind", "inputs", "outputs", "attributes", "numeric"},
            set(),
            f"operation {index}",
        )
        operation_id = require_identifier(raw["id"], f"operation {index}.id")
        if operation_id in seen:
            raise ModelGraphError(f"duplicate operation id {operation_id!r}")
        seen.add(operation_id)
        kind = raw["kind"]
        if kind not in KNOWN_OPERATION_KINDS:
            raise ModelGraphError(
                f"operation {operation_id!r} has unknown kind {kind!r}"
            )
        raw_inputs = raw["inputs"]
        raw_outputs = raw["outputs"]
        if (
            not isinstance(raw_inputs, list)
            or not raw_inputs
            or not isinstance(raw_outputs, list)
            or not raw_outputs
        ):
            raise ModelGraphError(
                f"operation {operation_id!r} requires explicit inputs and outputs"
            )
        inputs = tuple(
            require_identifier(value, f"operation {operation_id}.inputs[{item_index}]")
            for item_index, value in enumerate(raw_inputs)
        )
        outputs = tuple(
            require_identifier(value, f"operation {operation_id}.outputs[{item_index}]")
            for item_index, value in enumerate(raw_outputs)
        )
        result.append(
            Operation(
                index,
                operation_id,
                kind,
                inputs,
                outputs,
                _mapping(raw["attributes"], f"operation {operation_id}.attributes"),
                _mapping(raw["numeric"], f"operation {operation_id}.numeric"),
            )
        )
    return tuple(result)


def _validate_graph(model: ModelGraph) -> None:
    tensors = model.tensor_by_id
    symbols = model.symbol_by_id
    available = {
        tensor.tensor_id
        for tensor in model.tensors
        if tensor.role in {"input", "weight", "constant", "state"}
    }
    produced: set[str] = set()
    for operation in model.operations:
        for input_id in operation.inputs:
            if input_id not in tensors:
                raise ModelGraphError(
                    f"operation {operation.operation_id!r} references unknown input {input_id!r}"
                )
            if input_id not in available:
                raise ModelGraphError(
                    f"operation {operation.operation_id!r} reads {input_id!r} before production"
                )
        for output_id in operation.outputs:
            if output_id not in tensors:
                raise ModelGraphError(
                    f"operation {operation.operation_id!r} references unknown output {output_id!r}"
                )
            output = tensors[output_id]
            if output.role not in {"activation", "output", "state"}:
                raise ModelGraphError(
                    f"operation {operation.operation_id!r} cannot write {output.role} tensor {output_id!r}"
                )
            if output_id in produced or (
                output_id in available and output.role != "state"
            ):
                raise ModelGraphError(f"tensor {output_id!r} has multiple producers")
            produced.add(output_id)
            available.add(output_id)

        if operation.kind == "MATMUL":
            _validate_matmul(operation, tensors, symbols)
        elif operation.kind == "ADD":
            _validate_add(operation, tensors, symbols)

    if not model.outputs or len(set(model.outputs)) != len(model.outputs):
        raise ModelGraphError("outputs must be non-empty and unique")
    for output_id in model.outputs:
        if output_id not in tensors or output_id not in produced:
            raise ModelGraphError(f"declared output {output_id!r} is not produced")
        if tensors[output_id].role != "output":
            raise ModelGraphError(f"declared output {output_id!r} lacks output role")


def _validate_matmul(
    operation: Operation,
    tensors: Mapping[str, Tensor],
    symbols: Mapping[str, Symbol],
) -> None:
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise ModelGraphError(
            f"MATMUL {operation.operation_id!r} requires two inputs and one output"
        )
    left, right = (tensors[name] for name in operation.inputs)
    output = tensors[operation.outputs[0]]
    left_shape = left.resolved_shape(symbols)
    right_shape = right.resolved_shape(symbols)
    output_shape = output.resolved_shape(symbols)
    if len(left_shape) != 2 or len(right_shape) != 2 or len(output_shape) != 2:
        raise ModelGraphError(f"MATMUL {operation.operation_id!r} requires rank-2 tensors")
    if right.role != "weight":
        raise ModelGraphError(
            f"MATMUL {operation.operation_id!r} right input must be a weight"
        )
    batch, reduction = left_shape
    rows, weight_reduction = right_shape
    if weight_reduction != reduction or output_shape != (batch, rows):
        raise ModelGraphError(
            f"MATMUL {operation.operation_id!r} has incompatible exact shapes"
        )
    if (
        operation.numeric
        != {
            "accumulator_dtype": "i32",
            "input_dtype": "i8",
            "output_dtype": "i32",
            "reduction_order": "ascending_k",
            "weight_dtype": "i8",
        }
        or left.dtype != "i8"
        or right.dtype != "i8"
        or output.dtype != "i32"
    ):
        if operation.numeric.get("profile") is None:
            raise ModelGraphError(
                f"MATMUL {operation.operation_id!r} lacks a qualified numeric contract"
            )


def _validate_add(
    operation: Operation,
    tensors: Mapping[str, Tensor],
    symbols: Mapping[str, Symbol],
) -> None:
    if len(operation.inputs) != 2 or len(operation.outputs) != 1:
        raise ModelGraphError(
            f"ADD {operation.operation_id!r} requires two inputs and one output"
        )
    left, right = (tensors[name] for name in operation.inputs)
    output = tensors[operation.outputs[0]]
    shapes = {
        left.resolved_shape(symbols),
        right.resolved_shape(symbols),
        output.resolved_shape(symbols),
    }
    if len(shapes) != 1:
        raise ModelGraphError(
            f"ADD {operation.operation_id!r} forbids implicit broadcasting"
        )
    if len({left.dtype, right.dtype, output.dtype}) != 1:
        raise ModelGraphError(f"ADD {operation.operation_id!r} requires one dtype")


def parse_model_graph(
    raw: dict[str, Any],
    *,
    require_initializers: bool,
) -> ModelGraph:
    try:
        exact_keys(
            raw,
            {
                "schema",
                "model_id",
                "numeric_profile",
                "symbols",
                "tensors",
                "operations",
                "outputs",
            },
            set(),
            "model graph",
        )
        if raw["schema"] != SCHEMA:
            raise ModelGraphError(f"unsupported model graph schema {raw['schema']!r}")
        model_id = require_identifier(raw["model_id"], "model_id")
        numeric_profile = raw["numeric_profile"]
        if numeric_profile not in KNOWN_NUMERIC_PROFILES:
            raise ModelGraphError(f"unknown numeric profile {numeric_profile!r}")
        symbols = _parse_symbols(raw["symbols"])
        symbol_by_id = {symbol.symbol_id: symbol for symbol in symbols}
        tensors = _parse_tensors(
            raw["tensors"],
            symbol_by_id,
            require_initializers=require_initializers,
        )
        operations = _parse_operations(raw["operations"])
        raw_outputs = raw["outputs"]
        if not isinstance(raw_outputs, list):
            raise ModelGraphError("outputs must be an array")
        outputs = tuple(
            require_identifier(value, f"outputs[{index}]")
            for index, value in enumerate(raw_outputs)
        )
        model = ModelGraph(
            model_id,
            numeric_profile,
            symbols,
            tensors,
            operations,
            outputs,
        )
        _validate_graph(model)
        return model
    except ModelGraphError:
        raise
    except ArtifactError as exc:
        raise ModelGraphError(str(exc)) from exc


def load_model_graph(
    path: Path,
    *,
    require_initializers: bool = True,
) -> ModelGraph:
    try:
        return parse_model_graph(
            load_strict_json(path),
            require_initializers=require_initializers,
        )
    except ArtifactError as exc:
        if isinstance(exc, ModelGraphError):
            raise
        raise ModelGraphError(str(exc)) from exc
