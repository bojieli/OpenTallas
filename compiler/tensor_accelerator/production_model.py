"""Strict production Model Graph IR for real tensor-accelerator workloads.

The executable integer fixture remains on ``opentallas.model_graph.v1``.  This
module defines the additive v2 contract used by real-model adapters.  V2 makes
the information that was intentionally absent from the fixture graph explicit:
source provenance, checkpoint bindings, phase-specific dataflow, structured
runtime predicates, and transactional architectural state effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_identifier,
    require_int,
    require_sha256,
    sha256_bytes,
)


SCHEMA = "opentallas.model_graph.v2"
PHASES = ("prefill", "decode")
PHASE_SET = frozenset(PHASES)
DTYPE_BITS = {
    "bool": 1,
    "i8": 8,
    "u8": 8,
    "i16": 16,
    "u16": 16,
    "i32": 32,
    "u32": 32,
    "i64": 64,
    "u64": 64,
    "bf16": 16,
    "fp32": 32,
    "fp8_e4m3fn": 8,
    "fp4_e2m1": 4,
    "mxfp4_e2m1": 4,
    "e8m0": 8,
}
TENSOR_ROLES = frozenset({"input", "weight", "constant", "activation", "output"})
STATE_INITIALIZATIONS = frozenset({"zero", "request", "checkpoint"})
STATE_TRANSACTION = "prepare_commit"
STATE_ACTIONS = frozenset({"read_committed", "prepare", "commit", "discard"})
COMPARISONS = frozenset({"eq", "ne", "lt", "le", "gt", "ge"})


class ProductionModelGraphError(ArtifactError):
    """Raised when a v2 graph is incomplete, ambiguous, or inconsistent."""


Dimension = int | str


@dataclass(frozen=True)
class RuntimeSymbol:
    symbol_id: str
    minimum: int
    maximum: int
    multiple_of: int
    default: int
    binding: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding": dict(self.binding),
            "default": self.default,
            "id": self.symbol_id,
            "maximum": self.maximum,
            "minimum": self.minimum,
            "multiple_of": self.multiple_of,
        }


@dataclass(frozen=True)
class CheckpointSource:
    tensor_name: str
    payload_sha256: str
    dtype: str
    shape: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dtype": self.dtype,
            "payload_sha256": self.payload_sha256,
            "shape": list(self.shape),
            "tensor_name": self.tensor_name,
        }


@dataclass(frozen=True)
class CheckpointBinding:
    checkpoint_lock_id: str
    sources: tuple[CheckpointSource, ...]
    transform: Mapping[str, Any]
    payload_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_lock_id": self.checkpoint_lock_id,
            "kind": "checkpoint",
            "payload_sha256": self.payload_sha256,
            "sources": [source.to_dict() for source in self.sources],
            "transform": dict(self.transform),
        }


@dataclass(frozen=True)
class ProductionTensor:
    index: int
    tensor_id: str
    dtype: str
    shape: tuple[Dimension, ...]
    role: str
    layout: str
    binding: CheckpointBinding | None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "dtype": self.dtype,
            "id": self.tensor_id,
            "layout": self.layout,
            "role": self.role,
            "shape": list(self.shape),
        }
        if self.binding is not None:
            result["binding"] = self.binding.to_dict()
        return result


@dataclass(frozen=True)
class StateResource:
    index: int
    state_id: str
    state_class: str
    dtype: str
    shape: tuple[Dimension, ...]
    layout: str
    initialization: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "class": self.state_class,
            "dtype": self.dtype,
            "id": self.state_id,
            "initialization": self.initialization,
            "layout": self.layout,
            "shape": list(self.shape),
            "transaction": STATE_TRANSACTION,
        }


@dataclass(frozen=True)
class StateEffect:
    action: str
    state_id: str

    def to_dict(self) -> dict[str, str]:
        return {"action": self.action, "state": self.state_id}


@dataclass(frozen=True)
class SourceAnchor:
    path: str
    symbol: str
    source_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "source_sha256": self.source_sha256,
            "symbol": self.symbol,
        }


@dataclass(frozen=True)
class ProductionOperation:
    index: int
    operation_id: str
    kind: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    phases: tuple[str, ...]
    predicate: Mapping[str, Any]
    attributes: Mapping[str, Any]
    numeric_contract: str
    source_anchor: SourceAnchor
    effects: tuple[StateEffect, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attributes": dict(self.attributes),
            "effects": [effect.to_dict() for effect in self.effects],
            "id": self.operation_id,
            "inputs": list(self.inputs),
            "kind": self.kind,
            "numeric_contract": self.numeric_contract,
            "outputs": list(self.outputs),
            "phases": list(self.phases),
            "predicate": _copy_json(self.predicate),
            "source_anchor": self.source_anchor.to_dict(),
        }


@dataclass(frozen=True)
class Entrypoint:
    phase: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    states: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "phase": self.phase,
            "states": list(self.states),
        }


@dataclass(frozen=True)
class ProductionModelGraph:
    graph_id: str
    model_id: str
    source: Mapping[str, str]
    numeric_profile: str
    symbols: tuple[RuntimeSymbol, ...]
    state_resources: tuple[StateResource, ...]
    tensors: tuple[ProductionTensor, ...]
    operations: tuple[ProductionOperation, ...]
    entrypoints: tuple[Entrypoint, ...]

    @property
    def symbol_by_id(self) -> dict[str, RuntimeSymbol]:
        return {symbol.symbol_id: symbol for symbol in self.symbols}

    @property
    def tensor_by_id(self) -> dict[str, ProductionTensor]:
        return {tensor.tensor_id: tensor for tensor in self.tensors}

    @property
    def state_by_id(self) -> dict[str, StateResource]:
        return {state.state_id: state for state in self.state_resources}

    def to_dict(self) -> dict[str, Any]:
        return {
            "entrypoints": [entrypoint.to_dict() for entrypoint in self.entrypoints],
            "graph_id": self.graph_id,
            "model_id": self.model_id,
            "numeric_profile": self.numeric_profile,
            "operations": [operation.to_dict() for operation in self.operations],
            "schema": SCHEMA,
            "source": dict(self.source),
            "state_resources": [state.to_dict() for state in self.state_resources],
            "symbols": [symbol.to_dict() for symbol in self.symbols],
            "tensors": [tensor.to_dict() for tensor in self.tensors],
        }


def _copy_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _copy_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_json(item) for item in value]
    return value


def compute_graph_id(raw: Mapping[str, Any]) -> str:
    """Compute the canonical v2 identity, excluding the identity field itself."""

    return sha256_bytes(
        canonical_json_bytes({key: value for key, value in raw.items() if key != "graph_id"})
    )


def _nonempty_ascii(value: Any, label: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProductionModelGraphError(f"{label} must be a nonempty stable string")
    if len(value) > maximum:
        raise ProductionModelGraphError(f"{label} exceeds {maximum} characters")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ProductionModelGraphError(f"{label} must be ASCII") from exc
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ProductionModelGraphError(f"{label} contains a control character")
    return value


def _relative_source_path(value: Any, label: str) -> str:
    parsed = _nonempty_ascii(value, label, maximum=256)
    if "\\" in parsed:
        raise ProductionModelGraphError(f"{label} must use POSIX separators")
    path = PurePosixPath(parsed)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProductionModelGraphError(f"{label} must be a safe relative source path")
    return parsed


def _dtype(value: Any, label: str) -> str:
    if value not in DTYPE_BITS:
        raise ProductionModelGraphError(f"{label} has unknown dtype {value!r}")
    return value


def _layout(value: Any, label: str) -> str:
    try:
        return require_identifier(value, label)
    except ArtifactError as exc:
        raise ProductionModelGraphError(str(exc)) from exc


def _shape(
    raw: Any,
    symbols: Mapping[str, RuntimeSymbol],
    label: str,
    *,
    static: bool = False,
) -> tuple[Dimension, ...]:
    if not isinstance(raw, list) or not raw or len(raw) > 8:
        raise ProductionModelGraphError(f"{label} must have rank 1 through 8")
    result: list[Dimension] = []
    maximum_elements = 1
    for index, dimension in enumerate(raw):
        item_label = f"{label}[{index}]"
        if isinstance(dimension, bool):
            raise ProductionModelGraphError(f"{item_label} is not a dimension")
        if isinstance(dimension, int):
            parsed: Dimension = require_int(
                dimension, item_label, minimum=1, maximum=1 << 40
            )
            maximum_elements *= parsed
        elif not static and isinstance(dimension, str) and dimension in symbols:
            parsed = dimension
            maximum_elements *= symbols[dimension].maximum
        else:
            raise ProductionModelGraphError(
                f"{item_label} references an unknown or non-static dimension"
            )
        if maximum_elements > 1 << 63:
            raise ProductionModelGraphError(f"{label} maximum element count overflows")
        result.append(parsed)
    return tuple(result)


def _parse_source(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ProductionModelGraphError("source must be an object")
    exact_keys(raw, {"repository", "revision", "source_lock_id"}, set(), "source")
    return {
        "repository": _nonempty_ascii(raw["repository"], "source.repository"),
        "revision": _nonempty_ascii(raw["revision"], "source.revision"),
        "source_lock_id": require_sha256(
            raw["source_lock_id"], "source.source_lock_id"
        ),
    }


def _parse_symbols(raw: Any) -> tuple[RuntimeSymbol, ...]:
    if not isinstance(raw, list) or not raw:
        raise ProductionModelGraphError("symbols must be a nonempty array")
    result: list[RuntimeSymbol] = []
    seen: set[str] = set()
    request_fields: set[str] = set()
    for index, item in enumerate(raw):
        label = f"symbol {index}"
        if not isinstance(item, dict):
            raise ProductionModelGraphError(f"{label} must be an object")
        exact_keys(
            item,
            {"id", "minimum", "maximum", "multiple_of", "default", "binding"},
            set(),
            label,
        )
        symbol_id = require_identifier(item["id"], f"{label}.id")
        if symbol_id in seen:
            raise ProductionModelGraphError(f"duplicate symbol id {symbol_id!r}")
        seen.add(symbol_id)
        minimum = require_int(item["minimum"], f"symbol {symbol_id}.minimum", minimum=1)
        maximum = require_int(
            item["maximum"],
            f"symbol {symbol_id}.maximum",
            minimum=minimum,
            maximum=1 << 40,
        )
        multiple = require_int(
            item["multiple_of"],
            f"symbol {symbol_id}.multiple_of",
            minimum=1,
            maximum=maximum,
        )
        default = require_int(
            item["default"],
            f"symbol {symbol_id}.default",
            minimum=minimum,
            maximum=maximum,
        )
        if minimum % multiple or maximum % multiple or default % multiple:
            raise ProductionModelGraphError(
                f"symbol {symbol_id!r} bounds/default violate multiple_of"
            )
        binding = item["binding"]
        if not isinstance(binding, dict):
            raise ProductionModelGraphError(f"symbol {symbol_id}.binding must be an object")
        kind = binding.get("kind")
        if kind == "request":
            exact_keys(binding, {"kind", "field"}, set(), f"symbol {symbol_id}.binding")
            field = require_identifier(binding["field"], f"symbol {symbol_id}.binding.field")
            if field in request_fields:
                raise ProductionModelGraphError(
                    f"duplicate runtime request field {field!r}"
                )
            request_fields.add(field)
            parsed_binding = {"field": field, "kind": "request"}
        elif kind == "compile_time":
            exact_keys(binding, {"kind"}, set(), f"symbol {symbol_id}.binding")
            if minimum != maximum or default != minimum:
                raise ProductionModelGraphError(
                    f"compile-time symbol {symbol_id!r} must have one fixed value"
                )
            parsed_binding = {"kind": "compile_time"}
        else:
            raise ProductionModelGraphError(
                f"symbol {symbol_id!r} has unknown binding kind {kind!r}"
            )
        result.append(
            RuntimeSymbol(symbol_id, minimum, maximum, multiple, default, parsed_binding)
        )
    return tuple(result)


def _parse_checkpoint_source(raw: Any, label: str) -> CheckpointSource:
    if not isinstance(raw, dict):
        raise ProductionModelGraphError(f"{label} must be an object")
    exact_keys(
        raw,
        {"tensor_name", "payload_sha256", "dtype", "shape"},
        set(),
        label,
    )
    return CheckpointSource(
        tensor_name=_nonempty_ascii(raw["tensor_name"], f"{label}.tensor_name"),
        payload_sha256=require_sha256(
            raw["payload_sha256"], f"{label}.payload_sha256"
        ),
        dtype=_dtype(raw["dtype"], f"{label}.dtype"),
        shape=tuple(
            require_int(value, f"{label}.shape[{index}]", minimum=1, maximum=1 << 40)
            for index, value in enumerate(raw["shape"])
        )
        if isinstance(raw["shape"], list) and 1 <= len(raw["shape"]) <= 8
        else _raise_shape(label),
    )


def _raise_shape(label: str) -> tuple[int, ...]:
    raise ProductionModelGraphError(f"{label}.shape must have rank 1 through 8")


def _parse_binding(
    raw: Any,
    tensor_id: str,
    dtype: str,
    shape: tuple[Dimension, ...],
) -> CheckpointBinding:
    label = f"tensor {tensor_id}.binding"
    if not isinstance(raw, dict):
        raise ProductionModelGraphError(f"{label} must be an object")
    exact_keys(
        raw,
        {"kind", "checkpoint_lock_id", "sources", "transform", "payload_sha256"},
        set(),
        label,
    )
    if raw["kind"] != "checkpoint":
        raise ProductionModelGraphError(f"{label}.kind must be 'checkpoint'")
    sources_raw = raw["sources"]
    if not isinstance(sources_raw, list) or not sources_raw:
        raise ProductionModelGraphError(f"{label}.sources must be nonempty")
    sources = tuple(
        _parse_checkpoint_source(source, f"{label}.sources[{index}]")
        for index, source in enumerate(sources_raw)
    )
    names = [source.tensor_name for source in sources]
    if len(set(names)) != len(names):
        raise ProductionModelGraphError(f"{label} contains duplicate source tensors")
    transform = raw["transform"]
    if not isinstance(transform, dict):
        raise ProductionModelGraphError(f"{label}.transform must be an object")
    transform_kind = transform.get("kind")
    if transform_kind == "identity":
        exact_keys(transform, {"kind"}, set(), f"{label}.transform")
        parsed_transform: dict[str, Any] = {"kind": "identity"}
    elif transform_kind == "canonical":
        exact_keys(
            transform,
            {"kind", "certificate_id"},
            set(),
            f"{label}.transform",
        )
        parsed_transform = {
            "certificate_id": require_sha256(
                transform["certificate_id"], f"{label}.transform.certificate_id"
            ),
            "kind": "canonical",
        }
    else:
        raise ProductionModelGraphError(
            f"{label} has unknown transform kind {transform_kind!r}"
        )
    payload_sha256 = require_sha256(raw["payload_sha256"], f"{label}.payload_sha256")
    if transform_kind == "identity":
        if len(sources) != 1:
            raise ProductionModelGraphError(
                f"identity binding for tensor {tensor_id!r} requires one source"
            )
        source = sources[0]
        if (
            any(isinstance(dimension, str) for dimension in shape)
            or source.shape != shape
            or source.dtype != dtype
            or source.payload_sha256 != payload_sha256
        ):
            raise ProductionModelGraphError(
                f"identity binding for tensor {tensor_id!r} differs from its source"
            )
    return CheckpointBinding(
        checkpoint_lock_id=require_sha256(
            raw["checkpoint_lock_id"], f"{label}.checkpoint_lock_id"
        ),
        sources=sources,
        transform=parsed_transform,
        payload_sha256=payload_sha256,
    )


def _parse_tensors(
    raw: Any,
    symbols: Mapping[str, RuntimeSymbol],
) -> tuple[ProductionTensor, ...]:
    if not isinstance(raw, list) or not raw:
        raise ProductionModelGraphError("tensors must be a nonempty array")
    result: list[ProductionTensor] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        label = f"tensor {index}"
        if not isinstance(item, dict):
            raise ProductionModelGraphError(f"{label} must be an object")
        exact_keys(
            item,
            {"id", "dtype", "shape", "role", "layout"},
            {"binding"},
            label,
        )
        tensor_id = require_identifier(item["id"], f"{label}.id")
        if tensor_id in seen:
            raise ProductionModelGraphError(f"duplicate tensor id {tensor_id!r}")
        seen.add(tensor_id)
        dtype = _dtype(item["dtype"], f"tensor {tensor_id}.dtype")
        role = item["role"]
        if role not in TENSOR_ROLES:
            raise ProductionModelGraphError(
                f"tensor {tensor_id!r} has unknown role {role!r}"
            )
        shape = _shape(
            item["shape"],
            symbols,
            f"tensor {tensor_id}.shape",
            static=role in {"weight", "constant"},
        )
        binding_raw = item.get("binding")
        if role in {"weight", "constant"}:
            if binding_raw is None:
                raise ProductionModelGraphError(
                    f"tensor {tensor_id!r} lacks an exact checkpoint binding"
                )
            binding = _parse_binding(binding_raw, tensor_id, dtype, shape)
        else:
            if binding_raw is not None:
                raise ProductionModelGraphError(
                    f"runtime tensor {tensor_id!r} must not have a checkpoint binding"
                )
            binding = None
        result.append(
            ProductionTensor(
                index=index,
                tensor_id=tensor_id,
                dtype=dtype,
                shape=shape,
                role=role,
                layout=_layout(item["layout"], f"tensor {tensor_id}.layout"),
                binding=binding,
            )
        )
    return tuple(result)


def _parse_states(
    raw: Any,
    symbols: Mapping[str, RuntimeSymbol],
) -> tuple[StateResource, ...]:
    if not isinstance(raw, list):
        raise ProductionModelGraphError("state_resources must be an array")
    result: list[StateResource] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        label = f"state resource {index}"
        if not isinstance(item, dict):
            raise ProductionModelGraphError(f"{label} must be an object")
        exact_keys(
            item,
            {"id", "class", "dtype", "shape", "layout", "initialization", "transaction"},
            set(),
            label,
        )
        state_id = require_identifier(item["id"], f"{label}.id")
        if state_id in seen:
            raise ProductionModelGraphError(f"duplicate state id {state_id!r}")
        seen.add(state_id)
        if item["initialization"] not in STATE_INITIALIZATIONS:
            raise ProductionModelGraphError(
                f"state {state_id!r} has unknown initialization"
            )
        if item["transaction"] != STATE_TRANSACTION:
            raise ProductionModelGraphError(
                f"state {state_id!r} must use prepare/commit transactions"
            )
        result.append(
            StateResource(
                index=index,
                state_id=state_id,
                state_class=require_identifier(item["class"], f"state {state_id}.class"),
                dtype=_dtype(item["dtype"], f"state {state_id}.dtype"),
                shape=_shape(item["shape"], symbols, f"state {state_id}.shape"),
                layout=_layout(item["layout"], f"state {state_id}.layout"),
                initialization=item["initialization"],
            )
        )
    return tuple(result)


def _parse_phases(raw: Any, label: str) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise ProductionModelGraphError(f"{label} must be a nonempty phase array")
    phases = tuple(raw)
    if any(phase not in PHASE_SET for phase in phases) or len(set(phases)) != len(phases):
        raise ProductionModelGraphError(f"{label} contains an unknown or duplicate phase")
    if phases != tuple(phase for phase in PHASES if phase in phases):
        raise ProductionModelGraphError(f"{label} is not in canonical phase order")
    return phases


def _parse_predicate(
    raw: Any,
    symbols: Mapping[str, RuntimeSymbol],
    label: str,
    *,
    depth: int = 0,
) -> dict[str, Any]:
    if depth > 16 or not isinstance(raw, dict):
        raise ProductionModelGraphError(f"{label} is not a bounded predicate object")
    kind = raw.get("kind")
    if kind == "always":
        exact_keys(raw, {"kind"}, set(), label)
        return {"kind": "always"}
    if kind == "compare":
        exact_keys(raw, {"kind", "symbol", "operator", "value"}, set(), label)
        symbol = require_identifier(raw["symbol"], f"{label}.symbol")
        if symbol not in symbols:
            raise ProductionModelGraphError(
                f"{label} references unknown runtime symbol {symbol!r}"
            )
        operator = raw["operator"]
        if operator not in COMPARISONS:
            raise ProductionModelGraphError(f"{label} has unknown comparison {operator!r}")
        value = require_int(
            raw["value"], f"{label}.value", minimum=-(1 << 63), maximum=(1 << 63) - 1
        )
        return {"kind": "compare", "operator": operator, "symbol": symbol, "value": value}
    if kind in {"all", "any"}:
        exact_keys(raw, {"kind", "terms"}, set(), label)
        terms = raw["terms"]
        if not isinstance(terms, list) or not 1 <= len(terms) <= 16:
            raise ProductionModelGraphError(f"{label}.terms must contain 1 through 16 predicates")
        return {
            "kind": kind,
            "terms": [
                _parse_predicate(term, symbols, f"{label}.terms[{index}]", depth=depth + 1)
                for index, term in enumerate(terms)
            ],
        }
    if kind == "not":
        exact_keys(raw, {"kind", "term"}, set(), label)
        return {
            "kind": "not",
            "term": _parse_predicate(raw["term"], symbols, f"{label}.term", depth=depth + 1),
        }
    raise ProductionModelGraphError(f"{label} has unknown predicate kind {kind!r}")


def _parse_anchor(raw: Any, label: str) -> SourceAnchor:
    if not isinstance(raw, dict):
        raise ProductionModelGraphError(f"{label} must be an object")
    exact_keys(raw, {"path", "symbol", "source_sha256"}, set(), label)
    return SourceAnchor(
        path=_relative_source_path(raw["path"], f"{label}.path"),
        symbol=_nonempty_ascii(raw["symbol"], f"{label}.symbol", maximum=256),
        source_sha256=require_sha256(raw["source_sha256"], f"{label}.source_sha256"),
    )


def _parse_effects(raw: Any, states: Mapping[str, StateResource], label: str) -> tuple[StateEffect, ...]:
    if not isinstance(raw, list):
        raise ProductionModelGraphError(f"{label} must be an array")
    result: list[StateEffect] = []
    for index, item in enumerate(raw):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            raise ProductionModelGraphError(f"{item_label} must be an object")
        exact_keys(item, {"action", "state"}, set(), item_label)
        action = item["action"]
        if action not in STATE_ACTIONS:
            raise ProductionModelGraphError(f"{item_label} has unknown state action")
        state_id = require_identifier(item["state"], f"{item_label}.state")
        if state_id not in states:
            raise ProductionModelGraphError(
                f"{item_label} references unknown state {state_id!r}"
            )
        result.append(StateEffect(action, state_id))
    return tuple(result)


def _parse_operations(
    raw: Any,
    symbols: Mapping[str, RuntimeSymbol],
    states: Mapping[str, StateResource],
) -> tuple[ProductionOperation, ...]:
    if not isinstance(raw, list) or not raw:
        raise ProductionModelGraphError("operations must be a nonempty array")
    result: list[ProductionOperation] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        label = f"operation {index}"
        if not isinstance(item, dict):
            raise ProductionModelGraphError(f"{label} must be an object")
        exact_keys(
            item,
            {
                "id",
                "kind",
                "inputs",
                "outputs",
                "phases",
                "predicate",
                "attributes",
                "numeric_contract",
                "source_anchor",
                "effects",
            },
            set(),
            label,
        )
        operation_id = require_identifier(item["id"], f"{label}.id")
        if operation_id in seen:
            raise ProductionModelGraphError(f"duplicate operation id {operation_id!r}")
        seen.add(operation_id)
        inputs = _identifier_array(item["inputs"], f"operation {operation_id}.inputs", nonempty=True)
        outputs = _identifier_array(item["outputs"], f"operation {operation_id}.outputs", nonempty=True)
        attributes = item["attributes"]
        if not isinstance(attributes, dict):
            raise ProductionModelGraphError(
                f"operation {operation_id}.attributes must be an object"
            )
        canonical_json_bytes(attributes)
        result.append(
            ProductionOperation(
                index=index,
                operation_id=operation_id,
                kind=require_identifier(item["kind"], f"operation {operation_id}.kind"),
                inputs=inputs,
                outputs=outputs,
                phases=_parse_phases(item["phases"], f"operation {operation_id}.phases"),
                predicate=_parse_predicate(
                    item["predicate"], symbols, f"operation {operation_id}.predicate"
                ),
                attributes=_copy_json(attributes),
                numeric_contract=require_identifier(
                    item["numeric_contract"], f"operation {operation_id}.numeric_contract"
                ),
                source_anchor=_parse_anchor(
                    item["source_anchor"], f"operation {operation_id}.source_anchor"
                ),
                effects=_parse_effects(
                    item["effects"], states, f"operation {operation_id}.effects"
                ),
            )
        )
    return tuple(result)


def _identifier_array(raw: Any, label: str, *, nonempty: bool) -> tuple[str, ...]:
    if not isinstance(raw, list) or (nonempty and not raw):
        qualifier = "nonempty " if nonempty else ""
        raise ProductionModelGraphError(f"{label} must be a {qualifier}array")
    values = tuple(
        require_identifier(value, f"{label}[{index}]")
        for index, value in enumerate(raw)
    )
    if len(set(values)) != len(values):
        raise ProductionModelGraphError(f"{label} contains duplicates")
    return values


def _parse_entrypoints(raw: Any) -> tuple[Entrypoint, ...]:
    if not isinstance(raw, list) or len(raw) != len(PHASES):
        raise ProductionModelGraphError(
            "entrypoints must contain exactly prefill and decode"
        )
    result: list[Entrypoint] = []
    for index, item in enumerate(raw):
        label = f"entrypoint {index}"
        if not isinstance(item, dict):
            raise ProductionModelGraphError(f"{label} must be an object")
        exact_keys(item, {"phase", "inputs", "outputs", "states"}, set(), label)
        phase = item["phase"]
        if phase != PHASES[index]:
            raise ProductionModelGraphError(
                "entrypoints must be in canonical prefill/decode order"
            )
        result.append(
            Entrypoint(
                phase=phase,
                inputs=_identifier_array(item["inputs"], f"{label}.inputs", nonempty=True),
                outputs=_identifier_array(item["outputs"], f"{label}.outputs", nonempty=True),
                states=_identifier_array(item["states"], f"{label}.states", nonempty=False),
            )
        )
    return tuple(result)


def _validate_graph(model: ProductionModelGraph) -> None:
    tensors = model.tensor_by_id
    states = model.state_by_id
    entrypoints = {entrypoint.phase: entrypoint for entrypoint in model.entrypoints}
    producers: dict[str, str] = {}
    consumers: set[str] = set()
    state_uses: set[str] = set()

    for entrypoint in model.entrypoints:
        for tensor_id in entrypoint.inputs:
            tensor = tensors.get(tensor_id)
            if tensor is None or tensor.role != "input":
                raise ProductionModelGraphError(
                    f"{entrypoint.phase} entrypoint input {tensor_id!r} is not an input tensor"
                )
        for tensor_id in entrypoint.outputs:
            tensor = tensors.get(tensor_id)
            if tensor is None or tensor.role != "output":
                raise ProductionModelGraphError(
                    f"{entrypoint.phase} entrypoint output {tensor_id!r} is not an output tensor"
                )
        unknown_states = sorted(set(entrypoint.states) - states.keys())
        if unknown_states:
            raise ProductionModelGraphError(
                f"{entrypoint.phase} entrypoint references unknown states {unknown_states}"
            )

    for operation in model.operations:
        for tensor_id in operation.inputs:
            if tensor_id not in tensors:
                raise ProductionModelGraphError(
                    f"operation {operation.operation_id!r} references unknown input {tensor_id!r}"
                )
            consumers.add(tensor_id)
        for tensor_id in operation.outputs:
            tensor = tensors.get(tensor_id)
            if tensor is None:
                raise ProductionModelGraphError(
                    f"operation {operation.operation_id!r} references unknown output {tensor_id!r}"
                )
            if tensor.role not in {"activation", "output"}:
                raise ProductionModelGraphError(
                    f"operation {operation.operation_id!r} cannot write {tensor.role} tensor {tensor_id!r}"
                )
            previous = producers.get(tensor_id)
            if previous is not None:
                raise ProductionModelGraphError(
                    f"tensor {tensor_id!r} has producers {previous!r} and {operation.operation_id!r}"
                )
            producers[tensor_id] = operation.operation_id
        for effect in operation.effects:
            state_uses.add(effect.state_id)
            for phase in operation.phases:
                if effect.state_id not in entrypoints[phase].states:
                    raise ProductionModelGraphError(
                        f"operation {operation.operation_id!r} accesses state {effect.state_id!r} "
                        f"outside the {phase} entrypoint boundary"
                    )

    for tensor in model.tensors:
        if tensor.role in {"activation", "output"} and tensor.tensor_id not in producers:
            raise ProductionModelGraphError(
                f"runtime tensor {tensor.tensor_id!r} has no producer"
            )
        if tensor.role in {"weight", "constant"} and tensor.tensor_id not in consumers:
            raise ProductionModelGraphError(
                f"checkpoint tensor {tensor.tensor_id!r} has no execution consumer"
            )
        if tensor.role == "input" and not any(
            tensor.tensor_id in entrypoint.inputs for entrypoint in model.entrypoints
        ):
            raise ProductionModelGraphError(
                f"input tensor {tensor.tensor_id!r} is absent from every entrypoint"
            )
    unused_states = sorted(states.keys() - state_uses)
    if unused_states:
        raise ProductionModelGraphError(
            f"state resources have no execution effect: {unused_states}"
        )

    immutable = {
        tensor.tensor_id
        for tensor in model.tensors
        if tensor.role in {"weight", "constant"}
    }
    for phase in PHASES:
        entrypoint = entrypoints[phase]
        available = immutable | set(entrypoint.inputs)
        prepared: set[str] = set()
        for operation in model.operations:
            if phase not in operation.phases:
                continue
            missing = sorted(set(operation.inputs) - available)
            if missing:
                raise ProductionModelGraphError(
                    f"operation {operation.operation_id!r} reads phase-unavailable "
                    f"tensors in {phase}: {missing}"
                )
            available.update(operation.outputs)
            for effect in operation.effects:
                state_id = effect.state_id
                if effect.action == "read_committed":
                    if state_id in prepared:
                        raise ProductionModelGraphError(
                            f"operation {operation.operation_id!r} reads committed state "
                            f"{state_id!r} while a prepare is open in {phase}"
                        )
                elif effect.action == "prepare":
                    if state_id in prepared:
                        raise ProductionModelGraphError(
                            f"state {state_id!r} has nested prepares in {phase}"
                        )
                    prepared.add(state_id)
                else:
                    if state_id not in prepared:
                        raise ProductionModelGraphError(
                            f"state {state_id!r} {effect.action} lacks a prepare in {phase}"
                        )
                    prepared.remove(state_id)
        if prepared:
            raise ProductionModelGraphError(
                f"{phase} leaves uncommitted prepared states {sorted(prepared)}"
            )
        missing_outputs = sorted(set(entrypoint.outputs) - available)
        if missing_outputs:
            raise ProductionModelGraphError(
                f"{phase} entrypoint outputs are not produced: {missing_outputs}"
            )


def parse_production_model_graph(raw: dict[str, Any]) -> ProductionModelGraph:
    """Parse and semantically validate one strict v2 Model Graph object."""

    try:
        exact_keys(
            raw,
            {
                "schema",
                "graph_id",
                "model_id",
                "source",
                "numeric_profile",
                "symbols",
                "state_resources",
                "tensors",
                "operations",
                "entrypoints",
            },
            set(),
            "production model graph",
        )
        if raw["schema"] != SCHEMA:
            raise ProductionModelGraphError(
                f"unsupported production model graph schema {raw['schema']!r}"
            )
        expected_graph_id = compute_graph_id(raw)
        graph_id = require_sha256(raw["graph_id"], "graph_id")
        if graph_id != expected_graph_id:
            raise ProductionModelGraphError(
                f"graph_id differs: {graph_id} != {expected_graph_id}"
            )
        symbols = _parse_symbols(raw["symbols"])
        symbol_by_id = {symbol.symbol_id: symbol for symbol in symbols}
        states = _parse_states(raw["state_resources"], symbol_by_id)
        state_by_id = {state.state_id: state for state in states}
        model = ProductionModelGraph(
            graph_id=graph_id,
            model_id=require_identifier(raw["model_id"], "model_id"),
            source=_parse_source(raw["source"]),
            numeric_profile=require_identifier(raw["numeric_profile"], "numeric_profile"),
            symbols=symbols,
            state_resources=states,
            tensors=_parse_tensors(raw["tensors"], symbol_by_id),
            operations=_parse_operations(
                raw["operations"], symbol_by_id, state_by_id
            ),
            entrypoints=_parse_entrypoints(raw["entrypoints"]),
        )
        _validate_graph(model)
        if model.to_dict() != raw:
            raise ProductionModelGraphError(
                "production model graph is valid but not in canonical structural form"
            )
        return model
    except ProductionModelGraphError:
        raise
    except ArtifactError as exc:
        raise ProductionModelGraphError(str(exc)) from exc


def load_production_model_graph(path: Any) -> ProductionModelGraph:
    """Load a strict JSON v2 Model Graph from ``path``."""

    try:
        return parse_production_model_graph(load_strict_json(path))
    except ProductionModelGraphError:
        raise
    except ArtifactError as exc:
        raise ProductionModelGraphError(str(exc)) from exc


__all__ = [
    "CheckpointBinding",
    "CheckpointSource",
    "Entrypoint",
    "ProductionModelGraph",
    "ProductionModelGraphError",
    "ProductionOperation",
    "ProductionTensor",
    "RuntimeSymbol",
    "SCHEMA",
    "SourceAnchor",
    "StateEffect",
    "StateResource",
    "compute_graph_id",
    "load_production_model_graph",
    "parse_production_model_graph",
]
