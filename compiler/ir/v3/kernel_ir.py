"""Backend-neutral Model Graph and Tensor Kernel IR, version 3.

ADR-003 section 15 makes this the only place model semantics are expressed, and
forbids it from containing any backend concept.  Concretely:

* the **Model Graph** owns source semantics -- tensors, phases, predicates,
  state effects, numeric-contract identities and generation entrypoints;
* the **Tensor Kernel IR** owns target-numeric operations, iteration domains,
  tensor views, dependencies, legal fusion boundaries and counter classes; and
* neither may name a ROM address, HBM address, SRAM bank, stage, queue,
  schedule slot, physical engine, or a storage-qualified operation such as
  ``ROM_MATMUL``.

Both the Qwen and the DeepSeek exporter must produce this one schema, and both
backends must consume it.  That is the mechanism that keeps four targets
comparable: they share their semantics and differ only in placement.

Weight tensors carry a :class:`CheckpointBinding` naming the file, byte range
and SHA-256 of their payload in the locked checkpoint.  A backend turns that
directly into an ABI 3.0 object source, so no target ever materialises a private
copy of a 16 GB or 156 GB weight image.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping, Sequence

from runtime.abi3.capability import canonical_json, digest_of

MODEL_GRAPH_SCHEMA = "opentallas.model_graph.v3"
KERNEL_IR_SCHEMA = "opentallas.tensor_kernel_ir.v3"

PHASES = ("prefill", "decode")

#: Neutral tensor roles.  ``state`` is mutable and session-bound.
ROLES = frozenset({"input", "weight", "constant", "activation", "state", "output"})

#: Neutral element types.  These name *architectural* formats, not storage.
DTYPES = frozenset(
    {
        "bf16",
        "fp16",
        "fp32",
        "fp8_e4m3fn",
        "fp8_e5m2",
        "mxfp4_e2m1",
        "e8m0",
        "i8",
        "u8",
        "i32",
        "u32",
        "i64",
        "u64",
        "bool",
    }
)

#: Frozen neutral operation registry.  A kind names *what* is computed, never
#: where an operand lives.  Every kind maps to exactly one ABI 3.0 engine
#: family/subopcode pair in ``compiler/ir/v3/lowering.py``.
OPERATION_KINDS = frozenset(
    {
        # movement and lookup
        "EMBEDDING_LOOKUP",
        "GATHER",
        "SCATTER",
        "COPY",
        "CONCAT",
        # contraction
        "MATMUL",
        "GROUPED_MATMUL",
        "ROUTED_MATMUL",
        # normalisation and elementwise
        "RMS_NORM",
        "HEAD_RMS_NORM",
        "ROPE",
        "ROPE_INVERSE",
        "ADD",
        "MUL",
        "SCALE",
        "SILU_MUL",
        "SWIGLU",
        "CONVERT",
        "QUANTIZE",
        "DEQUANTIZE",
        "HADAMARD",
        "SOFTMAX",
        "SQRT_SOFTPLUS",
        "SIGMOID",
        # attention
        "ATTENTION_DENSE",
        "ATTENTION_GQA",
        "ATTENTION_SPARSE",
        "INDEX_SCORE",
        "WINDOW_INDEX",
        # compression and hyper-connections
        "COMPRESS_PROJECT",
        "COMPRESS_POOL",
        "COMPRESS_STATE_UPDATE",
        "HYPER_CONNECT_PRE",
        "HYPER_CONNECT_POST",
        "HYPER_CONNECT_HEAD",
        # routing
        "ROUTER_SCORE",
        "TOPK",
        "BIASED_TOPK",
        "HASH_ROUTE",
        "INDEX_TOPK",
        "WEIGHT_NORMALIZE",
        "EXPERT_DISPATCH",
        "EXPERT_REDUCE",
        # reduction and selection
        "ORDERED_SUM",
        "PARTITION_SUM",
        "LAST_TOKEN_SELECT",
        "VOCAB_PROJECT",
        "ARGMAX",
        "TOKEN_APPEND",
        # state
        "STATE_READ",
        "STATE_PREPARE",
        "STATE_COMMIT",
        "KV_APPEND",
    }
)

#: Terms that must never appear in a neutral IR document.  The checker scans
#: identifiers and attribute keys for these, which catches the failure mode
#: ADR-003 section 15 exists to prevent.
FORBIDDEN_TERMS = (
    "rom_",
    "_rom",
    "hbm",
    "sram",
    "dram",
    "bank",
    "stage",
    "queue",
    "slot",
    "address",
    "physical",
    "wafer",
    "reticle",
    "netlist",
    "tile_address",
)


class IRError(ValueError):
    """Raised when an IR document violates the neutral contract."""


@dataclass(frozen=True, slots=True)
class Symbolic:
    """A dimension that is a runtime symbol, optionally scaled."""

    symbol: str
    multiplier: int = 1
    maximum: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "multiplier": self.multiplier,
            "maximum": self.maximum,
        }


Extent = int | Symbolic


def _extent_dict(value: Extent) -> Any:
    return value.to_dict() if isinstance(value, Symbolic) else int(value)


@dataclass(frozen=True, slots=True)
class BindingSegment:
    """One authenticated byte range contributing to a segmented binding."""

    source_name: str
    path: str
    offset: int
    bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "path": self.path,
            "offset": self.offset,
            "bytes": self.bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class CheckpointBinding:
    """Where a weight's payload lives in the locked checkpoint.

    A binding is usually one contiguous range. ``segments`` covers the case a
    single range cannot express: a *bank* of weights that the model addresses
    as one operand but the checkpoint stores apart. DeepSeek's 256 routed
    experts per layer are the motivating case -- they are interleaved and
    lexicographically ordered in the shards, so no single range covers a bank,
    and without this the operand would have to travel as an attribute holding a
    list of tensor names, which is not an operand at all.

    When ``segments`` is present the payload is their ordered concatenation,
    ``bytes`` is the total, and each segment carries its own digest so
    verification stays incremental rather than requiring the assembled image.
    """

    source_name: str
    path: str
    offset: int
    bytes: int
    sha256: str
    transform: str = "identity"
    segments: tuple[BindingSegment, ...] = ()

    def __post_init__(self) -> None:
        if self.segments:
            total = sum(segment.bytes for segment in self.segments)
            if total != self.bytes:
                raise IRError(
                    f"binding {self.source_name}: segments cover {total} bytes, "
                    f"the binding declares {self.bytes}"
                )

    @property
    def is_segmented(self) -> bool:
        return bool(self.segments)

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "source_name": self.source_name,
            "path": self.path,
            "offset": self.offset,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "transform": self.transform,
        }
        if self.segments:
            body["segments"] = [segment.to_dict() for segment in self.segments]
        return body


@dataclass(frozen=True, slots=True)
class Tensor:
    """One neutral tensor."""

    tensor_id: str
    dtype: str
    shape: tuple[Extent, ...]
    role: str
    binding: CheckpointBinding | None = None
    scale_tensor_id: str | None = None
    scale_block_elements: int = 0
    generator: str = ""
    """Names a deterministic generator for a *derived* constant.

    A rotary coefficient table, a causal window index table and a compressed
    group enumeration are all constants that no checkpoint contains: they are
    computed from declared parameters. Requiring a checkpoint binding for every
    constant made them impossible to declare at all, so they had to travel as
    attributes -- which meant the operand slot the conventions document gives
    them (``VECTOR.ROPE`` in1, "coefficient rows") could not be filled.
    """

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "tensor_id": self.tensor_id,
            "dtype": self.dtype,
            "shape": [_extent_dict(d) for d in self.shape],
            "role": self.role,
        }
        if self.generator:
            body["generator"] = self.generator
        if self.binding is not None:
            body["binding"] = self.binding.to_dict()
        if self.scale_tensor_id is not None:
            body["scale_tensor_id"] = self.scale_tensor_id
            body["scale_block_elements"] = self.scale_block_elements
        return body


@dataclass(frozen=True, slots=True)
class StateResource:
    """One session-bound mutable resource."""

    state_id: str
    state_class: str
    dtype: str
    row_elements: int
    capacity_rows: Extent
    initialization: str = "zero"

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "state_class": self.state_class,
            "dtype": self.dtype,
            "row_elements": self.row_elements,
            "capacity_rows": _extent_dict(self.capacity_rows),
            "initialization": self.initialization,
        }


@dataclass(frozen=True, slots=True)
class Kernel:
    """One target-numeric operation with its iteration domain."""

    index: int
    kernel_id: str
    kind: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    numeric_contract: str
    iteration_domain: Mapping[str, Extent] = dc_field(default_factory=dict)
    attributes: Mapping[str, Any] = dc_field(default_factory=dict)
    phases: tuple[str, ...] = PHASES
    state_reads: tuple[str, ...] = ()
    state_writes: tuple[str, ...] = ()
    counter_class: str = ""
    source_operation_id: str = ""
    layer: int | None = None
    predicate: str = ""
    """Names an earlier kernel's boolean output that guards this kernel.

    DeepSeek's compressor runs its pool/norm/rope/quantise/commit chain only at
    ratio boundaries, and the source graph carries that as a first-class guard.
    With no predicate field the guard could only travel as an attribute, which
    a backend is under no obligation to honour -- so the choice was between
    always running the chain, which is wrong, and trusting an unenforced hint.
    ABI 3.0 already carries predicates on its instructions and loop
    descriptors; the neutral IR was the only layer missing one.
    """

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "index": self.index,
            "kernel_id": self.kernel_id,
            "kind": self.kind,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "numeric_contract": self.numeric_contract,
            "iteration_domain": {
                k: _extent_dict(v) for k, v in sorted(self.iteration_domain.items())
            },
            "attributes": _canonical_attributes(self.attributes),
            "phases": list(self.phases),
            "state_reads": list(self.state_reads),
            "state_writes": list(self.state_writes),
            "counter_class": self.counter_class,
            "source_operation_id": self.source_operation_id,
        }
        if self.predicate:
            body["predicate"] = self.predicate
        if self.layer is not None:
            body["layer"] = self.layer
        return body


def _canonical_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in sorted(attributes.items()):
        if isinstance(value, Symbolic):
            out[key] = value.to_dict()
        elif isinstance(value, (list, tuple)):
            out[key] = [
                v.to_dict() if isinstance(v, Symbolic) else v for v in value
            ]
        else:
            out[key] = value
    return out


@dataclass(frozen=True, slots=True)
class Entrypoint:
    phase: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    states: tuple[str, ...]
    generation_policy: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "states": list(self.states),
            "generation_policy": self.generation_policy,
        }


@dataclass(frozen=True, slots=True)
class RuntimeSymbol:
    name: str
    minimum: int
    maximum: int
    multiple_of: int = 1
    binding: str = "request"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "multiple_of": self.multiple_of,
            "binding": self.binding,
        }


@dataclass
class KernelGraph:
    """A complete neutral Tensor Kernel IR document."""

    model_id: str
    source: Mapping[str, Any]
    symbols: tuple[RuntimeSymbol, ...]
    tensors: tuple[Tensor, ...]
    states: tuple[StateResource, ...]
    kernels: tuple[Kernel, ...]
    entrypoints: tuple[Entrypoint, ...]
    numeric_profile: str = "target_precision_v1"
    generation_policy: Mapping[str, Any] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema": KERNEL_IR_SCHEMA,
            "model_id": self.model_id,
            "source": dict(sorted(self.source.items())),
            "numeric_profile": self.numeric_profile,
            "symbols": [s.to_dict() for s in self.symbols],
            "tensors": [t.to_dict() for t in self.tensors],
            "states": [s.to_dict() for s in self.states],
            "kernels": [k.to_dict() for k in self.kernels],
            "entrypoints": [e.to_dict() for e in self.entrypoints],
            "generation_policy": dict(sorted(self.generation_policy.items())),
        }
        return body

    @property
    def graph_id(self) -> str:
        return digest_of(self.to_dict())

    def tensor(self, tensor_id: str) -> Tensor:
        try:
            return self._index[tensor_id]
        except AttributeError:
            self._index = {t.tensor_id: t for t in self.tensors}  # type: ignore[attr-defined]
            return self._index[tensor_id]
        except KeyError:
            raise IRError(f"unknown tensor {tensor_id!r}") from None


    def write(self, path) -> str:
        from pathlib import Path

        body = self.to_dict()
        body["graph_id"] = self.graph_id
        Path(path).write_bytes(canonical_json(body))
        return body["graph_id"]

    # -- reading ---------------------------------------------------------
    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "KernelGraph":
        """Rebuild a graph from its published JSON.

        The published document is the interface between the exporters and the
        backends, so this is the only sanctioned way to read one: it rejects a
        foreign schema and re-derives ``graph_id``, which means a document
        edited after publication cannot be silently consumed.
        """
        if body.get("schema") != KERNEL_IR_SCHEMA:
            raise IRError(
                f"expected schema {KERNEL_IR_SCHEMA!r}, got {body.get('schema')!r}"
            )
        graph = cls(
            model_id=body["model_id"],
            source=dict(body.get("source", {})),
            numeric_profile=body.get("numeric_profile", "target_precision_v1"),
            symbols=tuple(RuntimeSymbol(**s) for s in body.get("symbols", [])),
            tensors=tuple(_tensor_from(t) for t in body.get("tensors", [])),
            states=tuple(_state_from(s) for s in body.get("states", [])),
            kernels=tuple(_kernel_from(k) for k in body.get("kernels", [])),
            entrypoints=tuple(
                Entrypoint(
                    phase=e["phase"],
                    inputs=tuple(e.get("inputs", ())),
                    outputs=tuple(e.get("outputs", ())),
                    states=tuple(e.get("states", ())),
                    generation_policy=e.get("generation_policy", ""),
                )
                for e in body.get("entrypoints", [])
            ),
            generation_policy=dict(body.get("generation_policy", {})),
        )
        declared = body.get("graph_id")
        if declared is not None and declared != graph.graph_id:
            raise IRError(
                f"graph_id {declared[:16]} does not match the document's content "
                f"digest {graph.graph_id[:16]}; the document was edited after "
                "publication"
            )
        return graph

    @classmethod
    def read(cls, path) -> "KernelGraph":
        from pathlib import Path

        return cls.from_dict(json.loads(Path(path).read_text()))


def _extent_from(value: Any) -> Extent:
    if isinstance(value, Mapping):
        return Symbolic(
            symbol=value["symbol"],
            multiplier=int(value.get("multiplier", 1)),
            maximum=int(value.get("maximum", 0)),
        )
    return int(value)


def _attributes_from(body: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in body.items():
        if isinstance(value, Mapping) and set(value) >= {"symbol", "multiplier"}:
            out[key] = _extent_from(value)
        elif isinstance(value, list):
            out[key] = [
                _extent_from(v)
                if isinstance(v, Mapping) and set(v) >= {"symbol", "multiplier"}
                else v
                for v in value
            ]
        else:
            out[key] = value
    return out


def _tensor_from(body: Mapping[str, Any]) -> Tensor:
    binding = body.get("binding")
    return Tensor(
        tensor_id=body["tensor_id"],
        dtype=body["dtype"],
        shape=tuple(_extent_from(d) for d in body["shape"]),
        role=body["role"],
        binding=_binding_from(binding) if binding else None,
        scale_tensor_id=body.get("scale_tensor_id"),
        scale_block_elements=int(body.get("scale_block_elements", 0)),
        generator=body.get("generator", ""),
    )


def _binding_from(body: Mapping[str, Any]) -> CheckpointBinding:
    segments = tuple(
        BindingSegment(**segment) for segment in body.get("segments", ())
    )
    return CheckpointBinding(
        source_name=body["source_name"],
        path=body["path"],
        offset=int(body["offset"]),
        bytes=int(body["bytes"]),
        sha256=body["sha256"],
        transform=body.get("transform", "identity"),
        segments=segments,
    )


def _state_from(body: Mapping[str, Any]) -> StateResource:
    return StateResource(
        state_id=body["state_id"],
        state_class=body["state_class"],
        dtype=body["dtype"],
        row_elements=int(body["row_elements"]),
        capacity_rows=_extent_from(body["capacity_rows"]),
        initialization=body.get("initialization", "zero"),
    )


def _kernel_from(body: Mapping[str, Any]) -> Kernel:
    return Kernel(
        index=int(body["index"]),
        kernel_id=body["kernel_id"],
        kind=body["kind"],
        inputs=tuple(body.get("inputs", ())),
        outputs=tuple(body.get("outputs", ())),
        numeric_contract=body["numeric_contract"],
        iteration_domain={
            k: _extent_from(v) for k, v in body.get("iteration_domain", {}).items()
        },
        attributes=_attributes_from(body.get("attributes", {})),
        phases=tuple(body.get("phases", PHASES)),
        state_reads=tuple(body.get("state_reads", ())),
        state_writes=tuple(body.get("state_writes", ())),
        counter_class=body.get("counter_class", ""),
        source_operation_id=body.get("source_operation_id", ""),
        layer=body.get("layer"),
        predicate=body.get("predicate", ""),
    )


# ---------------------------------------------------------------------------
# Neutrality and structural checking
# ---------------------------------------------------------------------------
def check_neutral(graph: KernelGraph) -> list[str]:
    """Return every neutrality or structural violation found in ``graph``."""
    errors: list[str] = []
    seen_tensor: dict[str, Tensor] = {}
    for tensor in graph.tensors:
        if tensor.tensor_id in seen_tensor:
            errors.append(f"duplicate tensor id {tensor.tensor_id!r}")
        seen_tensor[tensor.tensor_id] = tensor
        if tensor.dtype not in DTYPES:
            errors.append(f"tensor {tensor.tensor_id}: unknown dtype {tensor.dtype!r}")
        if tensor.role not in ROLES:
            errors.append(f"tensor {tensor.tensor_id}: unknown role {tensor.role!r}")
        if tensor.role == "weight" and tensor.binding is None:
            errors.append(
                f"tensor {tensor.tensor_id}: weight without a checkpoint binding"
            )
        if (
            tensor.role == "constant"
            and tensor.binding is None
            and not tensor.generator
        ):
            errors.append(
                f"tensor {tensor.tensor_id}: constant has neither a checkpoint "
                "binding nor a declared generator"
            )
        errors.extend(_scan_term(tensor.tensor_id, f"tensor {tensor.tensor_id}"))

    state_ids = {s.state_id for s in graph.states}
    produced: dict[str, int] = {}
    for kernel in graph.kernels:
        where = f"kernel {kernel.index} ({kernel.kernel_id})"
        if kernel.kind not in OPERATION_KINDS:
            errors.append(f"{where}: kind {kernel.kind!r} is not in the neutral registry")
        for phase in kernel.phases:
            if phase not in PHASES:
                errors.append(f"{where}: unknown phase {phase!r}")
        for name in kernel.inputs:
            if name not in seen_tensor:
                errors.append(f"{where}: input {name!r} is not a declared tensor")
        for name in kernel.outputs:
            if name not in seen_tensor:
                errors.append(f"{where}: output {name!r} is not a declared tensor")
            elif name in produced:
                errors.append(
                    f"{where}: tensor {name!r} already produced by kernel "
                    f"{produced[name]}; the IR is single assignment"
                )
            else:
                produced[name] = kernel.index
        for name in (*kernel.state_reads, *kernel.state_writes):
            if name not in state_ids:
                errors.append(f"{where}: unknown state resource {name!r}")
        if not kernel.numeric_contract:
            errors.append(f"{where}: no numeric contract named")
        if kernel.predicate:
            if kernel.predicate not in produced:
                errors.append(
                    f"{where}: predicate {kernel.predicate!r} is not produced by "
                    "an earlier kernel"
                )
            elif seen_tensor.get(kernel.predicate) is not None and (
                seen_tensor[kernel.predicate].dtype != "bool"
            ):
                errors.append(
                    f"{where}: predicate {kernel.predicate!r} is "
                    f"{seen_tensor[kernel.predicate].dtype}, not bool"
                )
        errors.extend(_scan_term(kernel.kernel_id, where))
        errors.extend(_scan_term(kernel.kind, where))
        for key in kernel.attributes:
            errors.extend(_scan_term(key, f"{where} attribute"))

    for index, kernel in enumerate(graph.kernels):
        if kernel.index != index:
            errors.append(f"kernel at position {index} declares index {kernel.index}")

    phases = {e.phase for e in graph.entrypoints}
    if phases != set(PHASES):
        errors.append(
            f"entrypoints cover {sorted(phases)}, expected {sorted(PHASES)}"
        )
    return errors


def _scan_term(text: str, where: str) -> list[str]:
    lowered = text.lower()
    return [
        f"{where}: neutral IR must not contain the backend term {term!r} "
        f"(found in {text!r})"
        for term in FORBIDDEN_TERMS
        if term in lowered
    ]


def require_neutral(graph: KernelGraph) -> None:
    errors = check_neutral(graph)
    if errors:
        raise IRError("neutral IR rejected:\n  " + "\n  ".join(errors))
