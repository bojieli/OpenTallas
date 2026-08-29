"""HBM/SRAM Physical Plan IR (TA-HBM-3.0 section 4.2).

The physical plan is the backend's own versioned, serialisable, digest-bound
statement of *where everything lives and how it is iterated*.  It is produced
from the neutral Tensor Kernel IR plus a capability, and is consumed by the ABI
3.0 emitter in :mod:`compiler.backends.hbm_sram.lower`.  Nothing physical is
ever written back into the neutral IR.

The plan answers five questions.

**Where do the weights live?**  Nowhere new.  A weight tensor carries a
:class:`~compiler.ir.v3.kernel_ir.CheckpointBinding` -- path, offset, bytes,
SHA-256 -- and the plan turns those byte ranges into memory objects whose
source is an *ordered list of the ranges themselves*.  A 16 GB Qwen image and a
156 GB DeepSeek image are therefore *described*, never copied and never relaid
out.  Tiling is expressed downstream by tensor-view strides.

The grouping rule is what makes the layer loop possible, so it is chosen
deliberately: **one object per weight role, spanning every layer, with the
segments concatenated in layer order**.  One object holds every layer's
``q_proj`` weight, another holds every layer's ``down_proj`` weight, and so on.
Because an object's logical address space is defined by the manifest rather
than by the file layout, layer ``L``'s payload then begins at exactly
``L * per_layer_bytes`` inside that object -- a constant stride -- even when the
checkpoint splits the layers across shard files at arbitrary boundaries.  The
alternative, grouping by file adjacency, produces a non-uniform stride the
moment a layer straddles a shard boundary and forces the program back into one
unrolled body per layer.  Each layer's payload also lies wholly inside its own
segment, so every view stays a zero-copy window into one authenticated range
rather than a gather across two.

Weights that no layer band claims -- embeddings, the final norm, the vocabulary
projection -- are grouped by file adjacency instead, which keeps the object
count in the low tens rather than the low thousands.

**How does one program cover many layers?**  By banding.  Layers whose kernel
structure and whose per-layer weight extents are uniform form a *layer band*,
and a band is emitted as one loop whose induction variable moves the weight
window.  A model with a dense prefix and an MoE suffix simply yields two bands;
nothing in this file knows which model that is.

**Where do activations live?**  In HBM arena slots sized by the declared symbol
maxima and reused by liveness, so that a 36-layer band needs one set of
buffers rather than 36.

**What does SRAM hold?**  Explicitly allocated, bank-assigned staging regions:
activation tiles, weight tiles, FP32 accumulators, attention working sets,
route buffers, state staging and link staging.  The plan carries the capacity
and bank-disjointness proofs.

**How is work spread over nodes?**  One node for a single-chip deployment,
exactly 32 for the cluster; the shard axis is the output-column axis of every
contraction, and the plan records which collectives must reassemble it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from compiler.ir.v3.kernel_ir import (
    CheckpointBinding,
    Entrypoint,
    Kernel,
    KernelGraph,
    RuntimeSymbol,
    StateResource,
    Symbolic,
    Tensor,
    require_neutral,
)
from compiler.ir.v3.lowering import engine_for
from compiler.ir.v3.numeric import canonical_contract_id
from runtime.abi3.capability import Capability, canonical_json, digest_of
from runtime.abi3.constants import (
    Attention,
    Dma,
    DTYPE_BITS,
    DType,
    Major,
    Route,
    Selection,
    StateClass,
    Tensor as TensorOp,
    TopologyClass,
    Vector,
)
from runtime.abi3.descriptors import Symbol

PLAN_SCHEMA = "opentallas.hbm_sram.physical_plan.v3"
PLAN_VERSION = "3.0.0"

#: Two checkpoint byte ranges are merged into one memory object when the second
#: begins at or just after the end of the first.  The slack absorbs the
#: alignment padding a checkpoint container inserts between tensors; the object
#: is the ordered *concatenation of the declared ranges*, so padding bytes are
#: never included and never copied.
SEGMENT_MERGE_SLACK = 4096

#: Neutral dtype -> ABI 3.0 storage element type.
DTYPE_MAP: Mapping[str, DType] = {
    "bf16": DType.BF16,
    "fp16": DType.FP16,
    "fp32": DType.FP32,
    "fp8_e4m3fn": DType.FP8_E4M3FN,
    "fp8_e5m2": DType.FP8_E5M2,
    "mxfp4_e2m1": DType.MXFP4_E2M1,
    "e8m0": DType.E8M0_SCALE,
    "i8": DType.I8,
    "u8": DType.U8,
    "i32": DType.I32,
    "u32": DType.U32,
    "i64": DType.I64,
    "u64": DType.U64,
    "bool": DType.U8,
}

#: Kernel kinds whose ABI operation contracts over a depth axis and therefore
#: gets the row / output-tile / depth-tile loop nest.
_CONTRACTION_SUBOPS = frozenset(
    {int(TensorOp.MATMUL), int(TensorOp.GROUPED_MATMUL), int(TensorOp.ROUTED_MATMUL)}
)

#: Kernel kinds that produce cluster traffic, and the traffic class each one
#: belongs to.  The classes are TA-HBM-3.0 section 3.6's ordered list.
LINK_CLASS_BY_KIND: Mapping[str, str] = {
    "EXPERT_DISPATCH": "expert_dispatch",
    "GATHER": "sparse_gather",
    "WINDOW_INDEX": "sparse_gather",
    "INDEX_TOPK": "sparse_gather",
    "ATTENTION_SPARSE": "sparse_gather",
    "EXPERT_REDUCE": "reduction",
    "ORDERED_SUM": "reduction",
    "PARTITION_SUM": "reduction",
}

LINK_CLASSES = (
    "expert_dispatch",
    "sparse_gather",
    "activation_transfer",
    "reduction",
    "coordinated_commit",
)


class PlanError(ValueError):
    """Raised when the neutral IR cannot be placed on this chip."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def dtype_of(name: str) -> DType:
    try:
        return DTYPE_MAP[name]
    except KeyError:
        raise PlanError(f"neutral dtype {name!r} has no ABI 3.0 storage type") from None


def element_bits(name: str) -> int:
    return DTYPE_BITS[dtype_of(name)]


def elements_in(byte_count: int, dtype: str) -> int:
    bits = element_bits(dtype)
    total = byte_count * 8
    if total % bits:
        raise PlanError(
            f"{byte_count} bytes is not a whole number of {dtype} elements"
        )
    return total // bits


def bytes_for(elements: int, dtype: str) -> int:
    bits = elements * element_bits(dtype)
    return (bits + 7) // 8


def choose_tile(extent: int, target: int) -> int:
    """Largest divisor of ``extent`` not exceeding ``target``.

    Divisor tiling removes edge tiles entirely: every tile of every loop is
    full, so one tensor view with one dynamic term covers the whole axis and
    the verifier's view-bound proof is exact rather than conservative.
    """
    if extent <= 0:
        raise PlanError(f"cannot tile a non-positive extent {extent}")
    limit = min(target, extent)
    for candidate in range(limit, 0, -1):
        if extent % candidate == 0:
            return candidate
    return 1


def round_up(value: int, multiple: int) -> int:
    if multiple <= 0:
        return value
    return ((value + multiple - 1) // multiple) * multiple


def _as_json(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _as_json(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_as_json(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Plan records
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class TileConfig:
    """Tile and block shapes.

    ``rows``/``cols``/``depth`` are the *hardware* tile the SCHEDULE descriptor
    carries: how one engine operation is decomposed across lanes, banks and
    passes.  ``block`` is the *program* token block, the only one of the four
    that becomes a loop, because the number of tokens is the thing that
    genuinely varies at runtime.  Actual tiles are the largest divisors of the
    real extents not exceeding these targets, so no tile is ever partial.

    ``block`` defaults to one token.  A larger block would retire fewer
    instructions, but a tensor view's extents are static while the token count
    is a runtime symbol, so the final block of a request would present rows the
    request does not have: attention would be asked for a query at a position
    with no key, and the KV append would write rows past the committed cursor.
    A block of one is the only extent that is exact for every span.  Raising it
    is safe exactly when the device bounds the final iteration's row extent from
    the loop's ``bound_symbol`` and ``bound_divisor``, which it does not yet do;
    ``build_plan`` accepts a larger block for that case.
    """

    rows: int = 64
    cols: int = 128
    depth: int = 128
    block: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "depth": self.depth,
            "block": self.block,
        }


@dataclass(frozen=True, slots=True)
class PlacedSegment:
    """One checkpoint byte range placed inside a memory object."""

    tensor_id: str
    source_name: str
    path: str
    file_offset: int
    bytes: int
    sha256: str
    element_offset: int
    elements: int
    dtype: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tensor_id": self.tensor_id,
            "source_name": self.source_name,
            "path": self.path,
            "file_offset": self.file_offset,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "element_offset": self.element_offset,
            "elements": self.elements,
            "dtype": self.dtype,
        }


@dataclass(frozen=True, slots=True)
class WeightGroup:
    """One immutable memory object built from adjacent checkpoint ranges."""

    group_id: str
    path: str
    size_bytes: int
    file_start: int
    file_end: int
    segments: tuple[PlacedSegment, ...]
    residency: str = "replicated"  # or "node_sharded"

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "file_start": self.file_start,
            "file_end": self.file_end,
            "segment_count": len(self.segments),
            "segments": [s.to_dict() for s in self.segments],
            "residency": self.residency,
        }


@dataclass(frozen=True, slots=True)
class GeneratedConstant:
    """A derived constant materialised by a declared deterministic generator.

    A rotary coefficient table exists in no checkpoint, so it cannot be a
    segment over authenticated bytes. The plan records the generator, its
    parameters and the digest of the result; the device materialises it and
    checks that digest. The backend never computes model numerics itself --
    ADR-003 section 15 forbids that -- it only carries the declaration through.
    """

    tensor_id: str
    generator: str
    parameters: Mapping[str, Any]
    size_bytes: int
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tensor_id": self.tensor_id,
            "generator": self.generator,
            "parameters": {k: v for k, v in sorted(self.parameters.items())},
            "size_bytes": self.size_bytes,
            "digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class WeightPlacement:
    """Where one weight tensor sits inside its group object."""

    tensor_id: str
    group_id: str
    element_offset: int
    elements: int
    dtype: str
    rows: int
    cols: int
    layer: int | None
    role_key: str
    layer_stride_elements: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "tensor_id": self.tensor_id,
            "group_id": self.group_id,
            "element_offset": self.element_offset,
            "elements": self.elements,
            "dtype": self.dtype,
            "rows": self.rows,
            "cols": self.cols,
            "layer": self.layer,
            "role_key": self.role_key,
            "layer_stride_elements": self.layer_stride_elements,
        }


@dataclass(frozen=True, slots=True)
class HbmPlacement:
    """One object's window in the node-local HBM address space.

    ADR-003 section 6.2 gives every memory object a base address, and the cycle
    model needs it: without one it cannot map an object onto channels and has to
    substitute a synthetic packed placement, which makes its channel and
    bank-conflict figures a property of the model rather than of this plan.  So
    the planner assigns the address, and the descriptor carries it.
    """

    key: str
    base_address: int
    size_bytes: int
    channel: int
    alignment_log2: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "base_address": self.base_address,
            "size_bytes": self.size_bytes,
            "channel": self.channel,
            "alignment_log2": self.alignment_log2,
        }


@dataclass(frozen=True, slots=True)
class ArenaSlot:
    """One reusable HBM activation buffer."""

    slot_id: str
    size_bytes: int
    rows: int
    cols: int
    dtype: str
    symbolic_rows: bool
    tenants: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "size_bytes": self.size_bytes,
            "rows": self.rows,
            "cols": self.cols,
            "dtype": self.dtype,
            "symbolic_rows": self.symbolic_rows,
            "tenants": list(self.tenants),
        }


@dataclass(frozen=True, slots=True)
class SramRegion:
    """One explicitly allocated, bank-assigned scratchpad region."""

    region_id: str
    purpose: str
    offset: int
    size_bytes: int
    elements: int
    dtype: str
    bank_first: int
    bank_count: int
    bank_mask: int
    port_mask: int
    lifetime: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "purpose": self.purpose,
            "offset": self.offset,
            "size_bytes": self.size_bytes,
            "elements": self.elements,
            "dtype": self.dtype,
            "bank_first": self.bank_first,
            "bank_count": self.bank_count,
            "bank_mask": self.bank_mask,
            "port_mask": self.port_mask,
            "lifetime": self.lifetime,
        }


@dataclass(frozen=True, slots=True)
class LayerBand:
    """A repeating block of layers emitted as one loop.

    ``period`` is how many layers one iteration covers.  It is usually one, but
    a model that alternates two layer structures -- dense attention on the even
    layers and sparse on the odd ones, say -- has period two, and the repeating
    unit is the *pair*.  Banding by period rather than by run of identical
    layers is what keeps such a model compressed without reordering it: the
    residual stream still flows layer by layer through the body.
    """

    band_id: int
    first_layer: int
    layer_count: int
    period: int
    signature: str
    body_kernels: tuple[int, ...]
    degraded: bool
    reason: str = ""

    @property
    def layers(self) -> tuple[int, ...]:
        """Every layer this band covers, in order."""
        return tuple(
            range(self.first_layer, self.first_layer + self.layer_count * self.period)
        )

    def iteration_layers(self, iteration: int) -> tuple[int, ...]:
        base = self.first_layer + iteration * self.period
        return tuple(range(base, base + self.period))

    def to_dict(self) -> dict[str, Any]:
        return {
            "band_id": self.band_id,
            "first_layer": self.first_layer,
            "layer_count": self.layer_count,
            "period": self.period,
            "signature": self.signature,
            "body_kernels": list(self.body_kernels),
            "degraded": self.degraded,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class StatePlacement:
    """One physical transactional state resource, possibly merged over layers."""

    physical_id: str
    state_class: str
    members: tuple[str, ...]
    row_elements: int
    row_bytes: int
    capacity_rows: int
    dtype: str
    band_id: int | None

    @property
    def size_bytes(self) -> int:
        return self.row_bytes * self.capacity_rows * len(self.members)

    def to_dict(self) -> dict[str, Any]:
        return {
            "physical_id": self.physical_id,
            "state_class": self.state_class,
            "members": list(self.members),
            "row_elements": self.row_elements,
            "row_bytes": self.row_bytes,
            "capacity_rows": self.capacity_rows,
            "dtype": self.dtype,
            "band_id": self.band_id,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class TopologyPlan:
    """One-node or exact 32-node deployment identity."""

    topology_class: int
    node_count: int
    shard_axis: str
    link_classes: tuple[str, ...]
    hbm_bytes_per_node: int
    sram_bytes_per_node: int
    peers_per_node: int
    chunk_bytes: int
    credit_bound: int
    virtual_channels: int
    retry_bound: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_class": self.topology_class,
            "node_count": self.node_count,
            "shard_axis": self.shard_axis,
            "link_classes": list(self.link_classes),
            "hbm_bytes_per_node": self.hbm_bytes_per_node,
            "sram_bytes_per_node": self.sram_bytes_per_node,
            "peers_per_node": self.peers_per_node,
            "chunk_bytes": self.chunk_bytes,
            "credit_bound": self.credit_bound,
            "virtual_channels": self.virtual_channels,
            "retry_bound": self.retry_bound,
        }


@dataclass(frozen=True, slots=True)
class LoopPlan:
    """One compact bounded loop the emitter will open."""

    loop_key: str
    kind: str  # layer | row | column | depth
    trip: int
    symbol: str
    divisor: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_key": self.loop_key,
            "kind": self.kind,
            "trip": self.trip,
            "symbol": self.symbol,
            "divisor": self.divisor,
        }


@dataclass(frozen=True, slots=True)
class OperandPlan:
    """How one kernel operand becomes a tensor view."""

    slot: int
    direction: str  # in | out
    tensor_id: str
    residence: str  # weight | arena | state | host | sram
    key: str
    dtype: str
    rows: int
    cols: int
    tile_rows: int
    tile_cols: int
    transposed: bool
    terms: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "direction": self.direction,
            "tensor_id": self.tensor_id,
            "residence": self.residence,
            "key": self.key,
            "dtype": self.dtype,
            "rows": self.rows,
            "cols": self.cols,
            "tile_rows": self.tile_rows,
            "tile_cols": self.tile_cols,
            "transposed": self.transposed,
            "terms": list(self.terms),
        }


@dataclass(frozen=True, slots=True)
class KernelPlan:
    """One neutral kernel's placement, tiling and loop nest."""

    index: int
    kernel_id: str
    kind: str
    engine_family: int
    engine_sub: int
    numeric_contract: str
    band_id: int | None
    layer: int | None
    body_position: int
    contraction: bool
    block_rows: int
    tile_rows: int
    tile_cols: int
    tile_depth: int
    row_loop: LoopPlan | None
    operands: tuple[OperandPlan, ...]
    aux: tuple[int, ...]
    slot_order: tuple[int, ...]
    groups: int
    phases: tuple[str, ...]
    link_class: str
    shard_columns: int
    depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "kernel_id": self.kernel_id,
            "kind": self.kind,
            "engine_family": self.engine_family,
            "engine_sub": self.engine_sub,
            "numeric_contract": self.numeric_contract,
            "band_id": self.band_id,
            "layer": self.layer,
            "body_position": self.body_position,
            "contraction": self.contraction,
            "block_rows": self.block_rows,
            "tile_rows": self.tile_rows,
            "tile_cols": self.tile_cols,
            "tile_depth": self.tile_depth,
            "row_loop": self.row_loop.to_dict() if self.row_loop else None,
            "operands": [o.to_dict() for o in self.operands],
            "aux": list(self.aux),
            "slot_order": list(self.slot_order),
            "groups": self.groups,
            "phases": list(self.phases),
            "link_class": self.link_class,
            "shard_columns": self.shard_columns,
            "depth": self.depth,
        }


@dataclass(frozen=True, slots=True)
class EmissionUnit:
    """One top-level unit of the emitted program."""

    kind: str  # kernel | band
    index: int  # kernel index, or band id

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "index": self.index}


@dataclass
class PhysicalPlan:
    """The complete, serialisable HBM/SRAM physical plan."""

    model_id: str
    graph_id: str
    capability_digest: str
    tile: TileConfig
    topology: TopologyPlan
    span_max: int
    weight_groups: tuple[WeightGroup, ...]
    weight_placements: tuple[WeightPlacement, ...]
    generated_constants: tuple[GeneratedConstant, ...]
    arena_slots: tuple[ArenaSlot, ...]
    hbm_map: Mapping[str, HbmPlacement]
    activation_keys: Mapping[str, str]
    arena_of_key: Mapping[str, str]
    sram_regions: tuple[SramRegion, ...]
    bands: tuple[LayerBand, ...]
    states: tuple[StatePlacement, ...]
    state_of_resource: Mapping[str, Sequence[Any]]
    state_of_tensor: Mapping[str, Sequence[Any]]
    kernels: tuple[KernelPlan, ...]
    units: tuple[EmissionUnit, ...]
    host_objects: Mapping[str, Mapping[str, Any]]
    proofs: Mapping[str, Any]
    warnings: tuple[str, ...] = ()

    # -- lookups ---------------------------------------------------------
    def placement(self, tensor_id: str) -> WeightPlacement:
        return self._weight_index[tensor_id]

    def kernel_plan(self, index: int) -> KernelPlan:
        return self._kernel_index[index]

    def band(self, band_id: int) -> LayerBand:
        return self._band_index[band_id]

    def state(self, physical_id: str) -> StatePlacement:
        return self._state_index[physical_id]

    def arena(self, slot_id: str) -> ArenaSlot:
        return self._arena_index[slot_id]

    def __post_init__(self) -> None:
        self._weight_index = {p.tensor_id: p for p in self.weight_placements}
        self._kernel_index = {k.index: k for k in self.kernels}
        self._band_index = {b.band_id: b for b in self.bands}
        self._state_index = {s.physical_id: s for s in self.states}
        self._arena_index = {a.slot_id: a for a in self.arena_slots}

    # -- serialisation ---------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PLAN_SCHEMA,
            "version": PLAN_VERSION,
            "model_id": self.model_id,
            "graph_id": self.graph_id,
            "capability_digest": self.capability_digest,
            "tile": self.tile.to_dict(),
            "topology": self.topology.to_dict(),
            "span_max": self.span_max,
            "weight_groups": [g.to_dict() for g in self.weight_groups],
            "generated_constants": [
                c.to_dict() for c in self.generated_constants
            ],
            "weight_placements": [p.to_dict() for p in self.weight_placements],
            "arena_slots": [a.to_dict() for a in self.arena_slots],
            "hbm_map": [
                self.hbm_map[key].to_dict() for key in sorted(self.hbm_map)
            ],
            "activation_keys": dict(sorted(self.activation_keys.items())),
            "arena_of_key": dict(sorted(self.arena_of_key.items())),
            "sram_regions": [r.to_dict() for r in self.sram_regions],
            "bands": [b.to_dict() for b in self.bands],
            "states": [s.to_dict() for s in self.states],
            "state_of_resource": {
                k: list(v) for k, v in sorted(self.state_of_resource.items())
            },
            "state_of_tensor": {
                k: list(v) for k, v in sorted(self.state_of_tensor.items())
            },
            "kernels": [k.to_dict() for k in self.kernels],
            "units": [u.to_dict() for u in self.units],
            "host_objects": _as_json(self.host_objects),
            "proofs": _as_json(self.proofs),
            "warnings": list(self.warnings),
        }

    @property
    def plan_id(self) -> str:
        return digest_of(self.to_dict())

    def write(self, path: Path | str) -> str:
        body = self.to_dict()
        body["plan_id"] = self.plan_id
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(canonical_json(body))
        return body["plan_id"]


# ---------------------------------------------------------------------------
# Neutral IR deserialisation
# ---------------------------------------------------------------------------
def read_kernel_graph(path: Path | str) -> KernelGraph:
    """Read a published Tensor Kernel IR v3 document.

    Deserialisation belongs to the frozen IR module, which re-derives
    ``graph_id`` and rejects a document edited after publication; a second
    implementation here could only drift from it.
    """
    return KernelGraph.read(path)


def as_kernel_graph(source: KernelGraph | Mapping[str, Any] | Path | str) -> KernelGraph:
    """Accept a graph, a published JSON body, or a path to one."""
    if isinstance(source, KernelGraph):
        return source
    if isinstance(source, Mapping):
        return KernelGraph.from_dict(source)
    return read_kernel_graph(source)


# ---------------------------------------------------------------------------
# Shape canonicalisation
# ---------------------------------------------------------------------------
def symbol_maximum(graph: KernelGraph, name: str, fallback: int) -> int:
    for symbol in graph.symbols:
        if symbol.name == name:
            return symbol.maximum if symbol.maximum > 0 else fallback
    return fallback


def _extent_value(extent: Any, span_max: int) -> tuple[int, bool]:
    """Return ``(static maximum, is_symbolic)`` for one declared extent."""
    if isinstance(extent, Symbolic):
        if extent.maximum > 0:
            return extent.maximum, True
        return max(span_max * max(extent.multiplier, 1), 1), True
    return int(extent), False


def matrix_shape(tensor: Tensor, span_max: int) -> tuple[int, int, bool]:
    """Canonical ``(rows, cols, rows_are_symbolic)`` for one tensor.

    Every tensor is treated as a matrix: the last declared axis is the width,
    and all leading axes fold into the row count.  That is the shape the tensor
    engines, the vector engines and the tensor-view descriptor all speak, and
    it keeps one view-construction rule for every operand in the graph.
    """
    if not tensor.shape:
        return 1, 1, False
    if isinstance(tensor.shape[0], Symbolic):
        # Token-major: one row per position, and everything the position
        # carries -- heads, key/value halves, head dimension -- folds into the
        # width.  Folding the head axis into the *rows* instead would make the
        # token-block loop count head-rows rather than tokens, and every view
        # in the body would step by the wrong stride.
        rows, _ = _extent_value(tensor.shape[0], span_max)
        cols = 1
        for axis in tensor.shape[1:]:
            # A symbolic axis after the position axis -- a sparse index width,
            # say -- contributes its declared maximum.  The *stride* stays
            # static, which is all a tensor view needs; the window is the worst
            # case and the tail padding is never executed (TA-ABI3-OPCONV-1
            # section 4.1).
            value, _ = _extent_value(axis, span_max)
            cols *= max(value, 1)
        return max(rows, 1), max(cols, 1), True
    cols, _ = _extent_value(tensor.shape[-1], span_max)
    rows = 1
    symbolic = False
    for axis in tensor.shape[:-1]:
        value, is_symbolic = _extent_value(axis, span_max)
        rows *= value
        symbolic = symbolic or is_symbolic
    return max(rows, 1), max(cols, 1), symbolic


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------
def build_plan(
    graph: KernelGraph | Mapping[str, Any] | str,
    capability: Capability,
    *,
    topology: TopologyClass | int | None = None,
    tile: TileConfig | None = None,
    validate: bool = True,
    unroll_layers: bool = False,
    reuse_arenas: bool = True,
    span_override: int | None = None,
) -> PhysicalPlan:
    """Produce the physical plan for ``graph`` on ``capability``.

    ``unroll_layers``, ``reuse_arenas`` and ``span_override`` exist for
    differential harnesses, and only for them.  A deployment that loops over
    layers and reuses activation buffers holds one residual buffer, not
    thirty-six, so a harness comparing *per-layer* activations against a
    reference cannot read them back -- every layer names the same memory.
    Turning banding and reuse off gives each tensor its own buffer at the cost
    of a much larger program and image, which is only affordable with a small
    ``span_override``.  The production build uses none of them, so nothing in
    the shipped artifact depends on a debugging mode.
    """
    graph = as_kernel_graph(graph)
    if validate:
        require_neutral(graph)
    tile = tile or TileConfig()
    warnings: list[str] = []
    topology_class = TopologyClass(
        capability.topology_class if topology is None else int(topology)
    )
    node_count = (
        int(capability.limits["max_nodes"])
        if topology_class is not TopologyClass.SINGLE_CHIP
        else 1
    )
    span_max = symbol_maximum(
        graph, "span_tokens", int(capability.limits["max_context_positions"])
    )
    if span_override is not None:
        span_max = max(int(span_override), 1)
    if span_max > capability.limits["max_context_positions"]:
        raise PlanError(
            f"graph declares span_tokens up to {span_max}, capability admits "
            f"{capability.limits['max_context_positions']}"
        )

    tensors = {t.tensor_id: t for t in graph.tensors}
    _check_numeric_contracts(graph, capability)

    bands, warnings_bands = _build_bands(graph, tensors)
    warnings.extend(warnings_bands)
    if unroll_layers:
        bands = _unrolled_bands(bands, graph)
        warnings.append(
            "layer banding is off: this is a diagnostic build, not a deployable "
            "one"
        )
    groups, placements = _place_weights(graph, bands, span_max)
    positions = position_inputs(graph)
    generated = _generated_constants(
        graph,
        int(capability.limits["max_context_positions"]),
        headroom=max(min(tile.block, round_up(span_max, tile.rows)), tile.rows, span_max),
    )
    for name in positions:
        warnings.append(
            f"input {name} is materialised from arange_u32_v1 and offset by "
            "POSITION_START; the request's position range is a bound symbol, "
            "not host data"
        )

    units, body_position, band_of_kernel = _emission_order(graph, bands)
    # One token block for the whole plan: the arena padding, the loop divisor
    # and every row-tiled view must agree on it.
    block = max(min(int(tile.block), span_max), 1)
    states, state_of_resource, warn_state = _place_states(
        graph, bands, band_of_kernel, span_max
    )
    warnings.extend(warn_state)
    state_of_tensor = _bind_state_tensors(graph, tensors, state_of_resource)
    activation_keys, arena_slots, arena_of_key, host_objects = _place_activations(
        graph,
        tensors,
        bands,
        units,
        body_position,
        band_of_kernel,
        span_max,
        block,
        state_of_tensor,
        reuse_arenas,
    )

    kernel_plans, warn_kernels = _plan_kernels(
        graph,
        tensors,
        placements,
        activation_keys,
        state_of_tensor,
        bands,
        band_of_kernel,
        body_position,
        span_max,
        tile,
        block,
        node_count,
        capability,
    )
    warnings.extend(warn_kernels)

    sram_regions = _allocate_sram(kernel_plans, capability, node_count, tile)
    hbm_map = _allocate_hbm(
        capability, groups, generated, states, arena_slots, host_objects
    )

    link = dict(capability.link)
    topology_plan = TopologyPlan(
        topology_class=int(topology_class),
        node_count=node_count,
        shard_axis="output_columns" if node_count > 1 else "none",
        link_classes=LINK_CLASSES if node_count > 1 else (),
        hbm_bytes_per_node=int(capability.memory["hbm"]["bytes"]),
        sram_bytes_per_node=int(capability.memory["sram"]["bytes"]),
        peers_per_node=int(link.get("peers_per_node", 0)),
        chunk_bytes=int(link.get("chunk_bytes", 1 << 16)),
        credit_bound=int(link.get("credit_bound", 8)),
        virtual_channels=int(link.get("virtual_channels", 1)),
        retry_bound=int(link.get("retry_bound", 3)),
    )

    proofs = _prove(
        capability,
        groups,
        arena_slots,
        sram_regions,
        states,
        kernel_plans,
        bands,
        node_count,
        host_objects,
        hbm_map,
    )

    plan = PhysicalPlan(
        model_id=graph.model_id,
        graph_id=graph.graph_id,
        capability_digest=capability.digest,
        tile=tile,
        topology=topology_plan,
        span_max=span_max,
        weight_groups=groups,
        generated_constants=generated,
        weight_placements=placements,
        arena_slots=arena_slots,
        hbm_map=hbm_map,
        activation_keys=activation_keys,
        arena_of_key=arena_of_key,
        sram_regions=sram_regions,
        bands=bands,
        states=states,
        state_of_resource=state_of_resource,
        state_of_tensor=state_of_tensor,
        kernels=kernel_plans,
        units=units,
        host_objects=host_objects,
        proofs=proofs,
        warnings=tuple(warnings),
    )
    return plan


def _check_numeric_contracts(graph: KernelGraph, capability: Capability) -> None:
    """Every contract the graph names must be one the capability implements.

    Both sides are canonicalised first: an exporter that emitted an
    implementation path rather than a semantic identifier would otherwise miss
    a contract the chip does in fact implement, and ADR-003 section 15 forbids
    the neutral IR from carrying an implementation location anyway.
    """
    implemented = {canonical_contract_id(c) for c in capability.numeric_contracts}
    missing = sorted(
        {
            canonical_contract_id(k.numeric_contract)
            for k in graph.kernels
            if k.numeric_contract
        }
        - implemented
    )
    if missing:
        raise PlanError(
            "capability does not implement the numeric contracts "
            f"{missing}; ADR-003 section 14 forbids silent emulation, so this "
            "must be fixed by characterising the contract, never by "
            "substituting a different one"
        )


# -- weights ----------------------------------------------------------------
def weight_roles(
    graph: KernelGraph, bands: Sequence[LayerBand]
) -> list[tuple[str, tuple[str, ...]]]:
    """Return ``(role_key, tensor ids in layer order)`` for every weight role.

    A *role* is one operand slot of one body position of one band: every
    layer's ``q_proj`` weight, say.  Roles are derived from the kernel
    structure, never from tensor names, so the rule holds for any exporter's
    naming convention.
    """
    by_index = {k.index: k for k in graph.kernels}
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)
    tensors = {t.tensor_id: t for t in graph.tensors}

    roles: list[tuple[str, tuple[str, ...]]] = []
    claimed: set[str] = set()
    for band in bands:
        blocks = [
            _block_kernels(by_layer, band.first_layer + i * band.period, band.period)
            for i in range(band.layer_count)
        ]
        body = [by_index[i] for i in band.body_kernels]
        for position, kernel in enumerate(body):
            for slot, name in enumerate(kernel.inputs):
                tensor = tensors[name]
                if tensor.role not in {"weight", "constant"} or tensor.binding is None:
                    continue
                members: list[str] = []
                for block in blocks:
                    if position >= len(block):
                        members = []
                        break
                    peer = block[position]
                    if slot >= len(peer.inputs):
                        members = []
                        break
                    member = peer.inputs[slot]
                    if (
                        member in claimed
                        or member in members
                        or tensors[member].binding is None
                    ):
                        # Already placed, or one tensor shared by every layer:
                        # either way this operand carries no per-layer stride and
                        # is left to the adjacency grouping below.
                        members = []
                        break
                    members.append(member)
                if not members:
                    continue
                claimed.update(members)
                roles.append((f"b{band.band_id}.p{position}.i{slot}", tuple(members)))
    return roles


def position_inputs(graph: KernelGraph) -> tuple[str, ...]:
    """Declared inputs whose content is the request's position range.

    A rank-one index vector over the token axis, read only as an index, holds
    ``POSITION_START + i`` and nothing else -- ADR-003 binds that range as a
    request symbol, and the submission carries it.  No accelerator moves such a
    vector across the host boundary per request: the address generator derives
    it.  The planner therefore materialises it from the frozen ``arange_u32_v1``
    generator and offsets the view by the ``POSITION_START`` symbol, which is
    the same values by construction and removes a host window that nothing
    could fill.  The substitution is recorded in the plan's warnings and in the
    deployment notes, because silently overriding a declared input is exactly
    how an exporter defect would hide.
    """
    consumers: dict[str, list[str]] = {}
    for kernel in graph.kernels:
        for name in kernel.inputs:
            consumers.setdefault(name, []).append(kernel.kind)
    out: list[str] = []
    for tensor in graph.tensors:
        if tensor.role != "input" or tensor.dtype not in {"u32", "i32"}:
            continue
        if len(tensor.shape) != 1 or not isinstance(tensor.shape[0], Symbolic):
            continue
        kinds = consumers.get(tensor.tensor_id, [])
        if not kinds or any(k == "EMBEDDING_LOOKUP" for k in kinds):
            continue  # the token stream, not a position range
        out.append(tensor.tensor_id)
    return tuple(sorted(out))


def _generated_constants(
    graph: KernelGraph, context_max: int = 0, headroom: int = 0
) -> tuple[GeneratedConstant, ...]:
    """Collect every derived constant, declared or implied by a position range."""
    from runtime.sim.generators import GeneratorError, digest_of, generate

    out: list[GeneratedConstant] = []
    for tensor_id in position_inputs(graph):
        # The window starts at POSITION_START and is a whole block wide, so the
        # table must reach one window past the last admissible start.
        count = max(int(context_max) + max(int(headroom), 1), 1)
        parameters = {"count": count}
        out.append(
            GeneratedConstant(
                tensor_id=tensor_id,
                generator="arange_u32_v1",
                parameters=parameters,
                size_bytes=int(generate("arange_u32_v1", parameters).nbytes),
                digest=digest_of("arange_u32_v1", parameters),
            )
        )
    for tensor in graph.tensors:
        if not tensor.generator:
            continue
        if tensor.role != "constant":
            raise PlanError(
                f"tensor {tensor.tensor_id} declares a generator but its role is "
                f"{tensor.role!r}; only a constant may be derived"
            )
        try:
            payload = generate(tensor.generator, tensor.generator_parameters)
            digest = digest_of(tensor.generator, tensor.generator_parameters)
        except GeneratorError as exc:
            raise PlanError(
                f"tensor {tensor.tensor_id}: {exc}"
            ) from None
        out.append(
            GeneratedConstant(
                tensor_id=tensor.tensor_id,
                generator=tensor.generator,
                parameters=dict(tensor.generator_parameters),
                size_bytes=int(payload.nbytes),
                digest=digest,
            )
        )
    return tuple(sorted(out, key=lambda c: c.tensor_id))


def _place_weights(
    graph: KernelGraph, bands: Sequence[LayerBand], span_max: int
) -> tuple[tuple[WeightGroup, ...], tuple[WeightPlacement, ...]]:
    """Build the zero-copy weight objects.

    Two rules, applied in order:

    1. one object per weight *role*, holding every layer's payload for that
       role as segments concatenated in layer order.  This is what gives the
       layer loop a constant stride however the checkpoint shards the file:
       layer ``L`` starts at ``L * per_layer_bytes`` inside the object because
       the object's address space is the manifest's, not the file's.  Each
       layer's payload lies wholly inside one segment, so the window a view
       takes is a zero-copy range rather than a gather across two.
    2. one object per run of *file-adjacent* leftover bindings -- embeddings,
       final norms, the vocabulary projection -- so the object count stays in
       the low tens.

    No byte is copied, relaid out, or counted twice: every object's source is
    the ordered list of authenticated checkpoint ranges themselves.
    """
    tensors = {t.tensor_id: t for t in graph.tensors}

    def _segment(tensor: Tensor, cursor: int) -> PlacedSegment:
        binding = tensor.binding
        assert binding is not None
        if binding.transform != "identity":
            raise PlanError(
                f"tensor {tensor.tensor_id}: checkpoint binding declares "
                f"transform {binding.transform!r}; this backend never relayouts "
                "a weight image, so a non-identity transform must be resolved "
                "in the checkpoint lock"
            )
        return PlacedSegment(
            tensor_id=tensor.tensor_id,
            source_name=binding.source_name,
            path=binding.path,
            file_offset=binding.offset,
            bytes=binding.bytes,
            sha256=binding.sha256,
            element_offset=elements_in(cursor, tensor.dtype),
            elements=elements_in(binding.bytes, tensor.dtype),
            dtype=tensor.dtype,
        )

    def _record(
        group_id: str,
        segment: PlacedSegment,
        layer: int | None,
        role_key: str,
        stride: int,
    ) -> WeightPlacement:
        tensor = tensors[segment.tensor_id]
        rows, cols, _ = matrix_shape(tensor, span_max)
        return WeightPlacement(
            tensor_id=segment.tensor_id,
            group_id=group_id,
            element_offset=segment.element_offset,
            elements=segment.elements,
            dtype=segment.dtype,
            rows=rows,
            cols=cols,
            layer=layer,
            role_key=role_key,
            layer_stride_elements=stride,
        )

    weight_groups: list[WeightGroup] = []
    placements: list[WeightPlacement] = []
    placed: set[str] = set()

    # (1) one object per weight role, segments in layer order.
    for role_key, members in weight_roles(graph, bands):
        group_id = f"wr{len(weight_groups):04d}"
        segments: list[PlacedSegment] = []
        cursor = 0
        for member in members:
            tensor = tensors[member]
            segments.append(_segment(tensor, cursor))
            cursor += tensor.binding.bytes  # type: ignore[union-attr]
        stride = segments[1].element_offset if len(segments) > 1 else 0
        paths = sorted({s.path for s in segments})
        weight_groups.append(
            WeightGroup(
                group_id=group_id,
                path=paths[0] if len(paths) == 1 else "<multi-shard>",
                size_bytes=cursor,
                file_start=min(s.file_offset for s in segments),
                file_end=max(s.file_offset + s.bytes for s in segments),
                segments=tuple(segments),
            )
        )
        for layer_index, segment in enumerate(segments):
            placements.append(_record(group_id, segment, layer_index, role_key, stride))
            placed.add(segment.tensor_id)

    # (2) leftovers, grouped by adjacency inside one checkpoint file.
    leftovers = [
        t
        for t in graph.tensors
        if t.role in {"weight", "constant"}
        and t.binding is not None
        and t.tensor_id not in placed
    ]
    leftovers.sort(key=lambda t: (t.binding.path, t.binding.offset, t.tensor_id))
    runs: list[dict[str, Any]] = []
    for tensor in leftovers:
        binding = tensor.binding
        assert binding is not None
        current = runs[-1] if runs else None
        adjacent = (
            current is not None
            and current["path"] == binding.path
            and 0 <= binding.offset - current["file_end"] <= SEGMENT_MERGE_SLACK
        )
        if not adjacent:
            current = {
                "path": binding.path,
                "file_start": binding.offset,
                "file_end": binding.offset,
                "cursor": 0,
                "segments": [],
            }
            runs.append(current)
        assert current is not None
        current["segments"].append(_segment(tensor, current["cursor"]))
        current["cursor"] += binding.bytes
        current["file_end"] = binding.offset + binding.bytes

    for body in runs:
        group_id = f"wg{len(weight_groups):04d}"
        weight_groups.append(
            WeightGroup(
                group_id=group_id,
                path=body["path"],
                size_bytes=body["cursor"],
                file_start=body["file_start"],
                file_end=body["file_end"],
                segments=tuple(body["segments"]),
            )
        )
        for segment in body["segments"]:
            placements.append(_record(group_id, segment, None, "", 0))

    placements.sort(key=lambda p: p.tensor_id)
    return tuple(weight_groups), tuple(placements)


# -- layer bands ------------------------------------------------------------
def _operand_class(
    tensors: Mapping[str, Tensor], producer: Mapping[str, int], name: str
) -> str:
    tensor = tensors[name]
    if tensor.role in {"weight", "constant"}:
        return "w"
    if tensor.role == "input":
        return "i"
    if tensor.role == "output":
        return "o"
    if name in producer:
        return "a"
    return "x"


def _layer_signature(
    kernels: Sequence[Kernel], tensors: Mapping[str, Tensor], producer: Mapping[str, int]
) -> str:
    parts = []
    for kernel in kernels:
        parts.append(
            "|".join(
                (
                    kernel.kind,
                    kernel.numeric_contract,
                    ",".join(_operand_class(tensors, producer, n) for n in kernel.inputs),
                    str(len(kernel.outputs)),
                    ",".join(sorted(kernel.phases)),
                    str(len(kernel.state_reads)),
                    str(len(kernel.state_writes)),
                )
            )
        )
    return ";".join(parts)


def _block_kernels(
    by_layer: Mapping[int, Sequence[Kernel]], first: int, period: int
) -> list[Kernel]:
    """The kernels of one iteration: ``period`` consecutive layers, in order."""
    body: list[Kernel] = []
    for offset in range(period):
        body.extend(by_layer.get(first + offset, ()))
    return body


def _build_bands(
    graph: KernelGraph, tensors: Mapping[str, Tensor]
) -> tuple[tuple[LayerBand, ...], list[str]]:
    """Fold repeating blocks of layers into bands.

    A band is the largest run of layers that repeats with some period: the same
    kernel sequence modulo the layer index, and the same weight extents at every
    operand, so the role object built in :func:`_place_weights` has a constant
    stride.  Period one is the ordinary homogeneous stack; period two is a model
    that alternates two attention forms.  Searching for a period rather than for
    a run of identical layers is what keeps such a model compressed *without*
    reordering it -- two interleaved single-layer bands would run every even
    layer before every odd one and break the residual chain.

    A run that admits no period is emitted one layer per band.  That is a
    correctness-preserving fallback, not a workaround: it is reported in the
    plan's warnings and shows up immediately as a larger instruction count.
    """
    warnings: list[str] = []
    producer = {
        name: kernel.index for kernel in graph.kernels for name in kernel.outputs
    }
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is None:
            continue
        by_layer.setdefault(kernel.layer, []).append(kernel)
    if not by_layer:
        return (), warnings

    layers = sorted(by_layer)
    for layer in layers:
        indices = [k.index for k in by_layer[layer]]
        if indices != list(range(indices[0], indices[0] + len(indices))):
            warnings.append(
                f"layer {layer} kernels are not a contiguous index block; the "
                "emitted body follows kernel order within the layer"
            )
    if layers != list(range(layers[0], layers[0] + len(layers))):
        warnings.append("layer indices are not contiguous; bands stop at each gap")

    signatures = {
        layer: _layer_signature(by_layer[layer], tensors, producer) for layer in layers
    }

    bands: list[LayerBand] = []
    cursor = 0
    while cursor < len(layers):
        first = layers[cursor]
        period, iterations = _longest_period(
            layers, cursor, signatures, by_layer, tensors
        )
        covered = period * iterations
        if iterations > 1:
            bands.append(
                LayerBand(
                    band_id=len(bands),
                    first_layer=first,
                    layer_count=iterations,
                    period=period,
                    signature=";".join(
                        signatures[first + offset] for offset in range(period)
                    ),
                    body_kernels=tuple(
                        k.index for k in _block_kernels(by_layer, first, period)
                    ),
                    degraded=False,
                )
            )
        else:
            for offset in range(max(covered, 1)):
                layer = first + offset
                bands.append(
                    LayerBand(
                        band_id=len(bands),
                        first_layer=layer,
                        layer_count=1,
                        period=1,
                        signature=signatures[layer],
                        body_kernels=tuple(k.index for k in by_layer[layer]),
                        degraded=True,
                        reason="no repeating block starts at this layer",
                    )
                )
        cursor += max(covered, 1)
    return tuple(bands), warnings


#: The largest repeating block the planner will look for.  A period beyond this
#: is more likely a structural irregularity than a design, and searching further
#: costs more than the compression it could win.
MAX_BAND_PERIOD = 8


def _longest_period(
    layers: Sequence[int],
    cursor: int,
    signatures: Mapping[int, str],
    by_layer: Mapping[int, Sequence[Kernel]],
    tensors: Mapping[str, Tensor],
) -> tuple[int, int]:
    """Return ``(period, iterations)`` for the band starting at ``layers[cursor]``."""
    first = layers[cursor]
    remaining = len(layers) - cursor
    best = (1, 1)
    for period in range(1, min(MAX_BAND_PERIOD, remaining) + 1):
        if any(first + offset not in signatures for offset in range(period)):
            break
        iterations = 1
        while (period * (iterations + 1)) <= remaining and _block_matches(
            first, period, iterations, layers, cursor, signatures
        ):
            iterations += 1
        if iterations < 2:
            continue
        uniform, reason = _uniform_weight_extents(
            first, period, iterations, by_layer, tensors
        )
        while not uniform and iterations > 1:
            iterations -= 1
            if iterations < 2:
                break
            uniform, reason = _uniform_weight_extents(
                first, period, iterations, by_layer, tensors
            )
        if iterations >= 2 and period * iterations > best[0] * best[1]:
            best = (period, iterations)
    return best


def _block_matches(
    first: int,
    period: int,
    iteration: int,
    layers: Sequence[int],
    cursor: int,
    signatures: Mapping[int, str],
) -> bool:
    for offset in range(period):
        position = cursor + iteration * period + offset
        if position >= len(layers):
            return False
        layer = layers[position]
        if layer != first + iteration * period + offset:
            return False
        if signatures.get(layer) != signatures[first + offset]:
            return False
    return True


def _uniform_weight_extents(
    first: int,
    period: int,
    iterations: int,
    by_layer: Mapping[int, Sequence[Kernel]],
    tensors: Mapping[str, Tensor],
) -> tuple[bool, str]:
    """Every iteration's payload for a weight role must have one byte extent."""
    if iterations < 2:
        return True, ""
    blocks = [
        _block_kernels(by_layer, first + i * period, period) for i in range(iterations)
    ]
    body = blocks[0]
    if any(len(block) != len(body) for block in blocks):
        return False, "iterations declare different kernel counts"
    for position, kernel in enumerate(body):
        for slot, name in enumerate(kernel.inputs):
            tensor = tensors[name]
            if tensor.role not in {"weight", "constant"}:
                continue
            if tensor.binding is None:
                return False, f"operand {position}.{slot} has no checkpoint binding"
            extents: set[tuple[int, str]] = set()
            seen: set[str] = set()
            for block in blocks:
                peer = block[position]
                if slot >= len(peer.inputs):
                    return False, f"operand {position}.{slot} is missing in a block"
                member = tensors[peer.inputs[slot]]
                if member.binding is None:
                    return False, (
                        f"operand {position}.{slot} of a later block has no "
                        "checkpoint binding"
                    )
                seen.add(peer.inputs[slot])
                extents.add((member.binding.bytes, member.dtype))
            if len(seen) == 1:
                continue  # one tensor shared by every iteration: stride zero
            if len(seen) != iterations:
                return False, (
                    f"operand {position}.{slot} is shared by some iterations and "
                    "private to others"
                )
            if len(extents) != 1:
                return False, (
                    f"operand {position}.{slot} has {len(extents)} distinct "
                    "payload extents across the run"
                )
    return True, ""


def _emission_order(
    graph: KernelGraph, bands: Sequence[LayerBand]
) -> tuple[tuple[EmissionUnit, ...], Mapping[int, int], Mapping[int, int]]:
    """Linearise the program: prologue kernels, band loops, epilogue kernels."""
    band_of_kernel: dict[int, int] = {}
    body_position: dict[int, int] = {}
    band_layers: dict[int, set[int]] = {}
    by_index = {k.index: k for k in graph.kernels}
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)
    # Every iteration's kernels get the body position of their band's body, so a
    # tensor produced at position p of one iteration and consumed at position q
    # of the next resolves to the same buffer -- which is exactly what makes the
    # residual stream legal across a layer-loop iteration.
    for band in bands:
        band_layers[band.band_id] = set(band.layers)
        for iteration in range(band.layer_count):
            position = 0
            for layer in band.iteration_layers(iteration):
                for kernel in by_layer.get(layer, ()):
                    body_position[kernel.index] = position
                    position += 1
    for layer, kernels in by_layer.items():
        for position, kernel in enumerate(kernels):
            body_position.setdefault(kernel.index, position)
    layer_to_band = {
        layer: band.band_id for band in bands for layer in band_layers[band.band_id]
    }

    units: list[EmissionUnit] = []
    emitted_bands: set[int] = set()
    for kernel in graph.kernels:
        if kernel.layer is None:
            units.append(EmissionUnit("kernel", kernel.index))
            continue
        band_id = layer_to_band[kernel.layer]
        band_of_kernel[kernel.index] = band_id
        if band_id in emitted_bands:
            continue
        band = bands[band_id]
        if kernel.index == band.body_kernels[0]:
            units.append(EmissionUnit("band", band_id))
            emitted_bands.add(band_id)
    return tuple(units), body_position, band_of_kernel


# -- activations ------------------------------------------------------------
def _place_activations(
    graph: KernelGraph,
    tensors: Mapping[str, Tensor],
    bands: Sequence[LayerBand],
    units: Sequence[EmissionUnit],
    body_position: Mapping[int, int],
    band_of_kernel: Mapping[int, int],
    span_max: int,
    block: int,
    state_of_tensor: Mapping[str, Sequence[Any]],
    reuse_arenas: bool = True,
) -> tuple[
    dict[str, str], tuple[ArenaSlot, ...], dict[str, str], dict[str, dict[str, Any]]
]:
    """Assign every activation tensor a reusable HBM arena slot.

    A tensor produced at body position ``p`` of band ``b`` gets the key
    ``b{b}.p{p}.o{slot}`` for *every* layer of the band, which is exactly what
    makes the layer loop legal: the residual stream that layer L reads is the
    buffer layer L-1 wrote, and the loop reuses it in place.
    """
    keys: dict[str, str] = {}
    host_objects: dict[str, dict[str, Any]] = {}
    ordinal: dict[str, int] = {}
    band_span: dict[int, tuple[int, int]] = {}

    # Assign one emission ordinal per kernel in program order.
    order: list[int] = []
    for unit in units:
        if unit.kind == "kernel":
            order.append(unit.index)
        else:
            band = bands[unit.index]
            start = len(order)
            order.extend(band.body_kernels)
            band_span[band.band_id] = (start, len(order) - 1)
    position_of = {index: pos for pos, index in enumerate(order)}

    by_index = {k.index: k for k in graph.kernels}
    for kernel in graph.kernels:
        band_id = band_of_kernel.get(kernel.index)
        for slot, name in enumerate(kernel.outputs):
            tensor = tensors[name]
            if (
                tensor.role in {"weight", "constant", "input", "output"}
                or name in state_of_tensor
                or (kernel.state_writes and tensor.role == "state")
            ):
                # Host-visible results keep their host identity even though a
                # kernel produces them; state effects live in state objects.
                continue
            if band_id is None:
                keys[name] = f"k{kernel.index}.o{slot}"
            else:
                keys[name] = f"b{band_id}.p{body_position[kernel.index]}.o{slot}"

    derived = set(position_inputs(graph))
    for tensor in graph.tensors:
        if tensor.role == "input" and tensor.tensor_id not in derived:
            keys.setdefault(tensor.tensor_id, f"host.in.{tensor.tensor_id}")
        elif tensor.role == "output":
            keys.setdefault(tensor.tensor_id, f"host.out.{tensor.tensor_id}")

    if reuse_arenas:
        _unify_loop_carried(graph, bands, keys)

    # Size and liveness.
    sizes: dict[str, tuple[int, int, int, str, bool]] = {}
    first_use: dict[str, int] = {}
    last_use: dict[str, int] = {}
    carried: set[str] = set()
    for kernel in graph.kernels:
        pos = position_of.get(kernel.index)
        if pos is None:
            continue
        for name in kernel.outputs:
            key = keys.get(name)
            if key is None:
                continue
            tensor = tensors[name]
            rows, cols, symbolic = matrix_shape(tensor, span_max)
            if symbolic:
                rows = round_up(rows, block)
            size = bytes_for(rows * cols, tensor.dtype)
            previous = sizes.get(key)
            if previous is None or size > previous[0]:
                sizes[key] = (size, rows, cols, tensor.dtype, symbolic)
            first_use.setdefault(key, pos)
            last_use[key] = max(last_use.get(key, pos), pos)
        for name in kernel.inputs:
            key = keys.get(name)
            if key is None:
                continue
            if key in first_use and pos < first_use[key]:
                carried.add(key)  # consumed by a later iteration of its own band
            last_use[key] = max(last_use.get(key, pos), pos)
            if key not in sizes:
                tensor = tensors[name]
                rows, cols, symbolic = matrix_shape(tensor, span_max)
                if symbolic:
                    rows = round_up(rows, block)
                sizes[key] = (
                    bytes_for(rows * cols, tensor.dtype),
                    rows,
                    cols,
                    tensor.dtype,
                    symbolic,
                )
                first_use.setdefault(key, pos)

    # A buffer that a band carries across iterations stays live for the whole
    # band; anything else is freed after its last consumer.
    for key in list(carried):
        for band_id, (start, end) in band_span.items():
            if start <= first_use.get(key, -1) <= end:
                first_use[key] = start
                last_use[key] = max(last_use.get(key, end), end)

    host_keys = sorted(k for k in sizes if k.startswith("host."))
    arena_keys = sorted(
        (k for k in sizes if not k.startswith("host.")),
        key=lambda k: (first_use.get(k, 0), k),
    )

    slots: list[dict[str, Any]] = []
    arena_of_key: dict[str, str] = {}
    for key in arena_keys:
        size, rows, cols, dtype, symbolic = sizes[key]
        chosen = None
        for slot in slots if reuse_arenas else ():
            if slot["size_bytes"] != size or slot["dtype"] != dtype:
                continue
            if slot["free_at"] <= first_use.get(key, 0):
                chosen = slot
                break
        if chosen is None:
            chosen = {
                "slot_id": f"arena{len(slots):04d}",
                "size_bytes": size,
                "rows": rows,
                "cols": cols,
                "dtype": dtype,
                "symbolic": symbolic,
                "tenants": [],
                "free_at": 0,
            }
            slots.append(chosen)
        chosen["tenants"].append(key)
        chosen["free_at"] = max(chosen["free_at"], last_use.get(key, 0) + 1)
        arena_of_key[key] = chosen["slot_id"]

    for key in host_keys:
        size, rows, cols, dtype, symbolic = sizes[key]
        host_objects[key] = {
            "key": key,
            "size_bytes": size,
            "rows": rows,
            "cols": cols,
            "dtype": dtype,
            "direction": "in" if key.startswith("host.in.") else "out",
        }

    arena_slots = tuple(
        ArenaSlot(
            slot_id=slot["slot_id"],
            size_bytes=slot["size_bytes"],
            rows=slot["rows"],
            cols=slot["cols"],
            dtype=slot["dtype"],
            symbolic_rows=slot["symbolic"],
            tenants=tuple(slot["tenants"]),
        )
        for slot in slots
    )
    return keys, arena_slots, arena_of_key, host_objects


def _unrolled_bands(
    bands: Sequence[LayerBand], graph: KernelGraph
) -> tuple[LayerBand, ...]:
    """One band per layer, for a diagnostic build that must be readable back."""
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)
    out: list[LayerBand] = []
    for band in bands:
        for layer in band.layers:
            out.append(
                LayerBand(
                    band_id=len(out),
                    first_layer=layer,
                    layer_count=1,
                    period=1,
                    signature=band.signature,
                    body_kernels=tuple(k.index for k in by_layer.get(layer, ())),
                    degraded=True,
                    reason="diagnostic unrolled build",
                )
            )
    return tuple(out)


def _unify_loop_carried(
    graph: KernelGraph, bands: Sequence[LayerBand], keys: dict[str, str]
) -> None:
    """Give a band's live-in and live-out value one buffer.

    A residual stream enters the first layer from the prologue and leaves the
    last layer for the epilogue, and in between each layer reads what the layer
    before it wrote.  Emitted as a loop, the body reads one buffer and writes
    another, so unless those are the *same* buffer every iteration would re-read
    the prologue's value and the stack would collapse to one layer applied
    thirty-six times to the embedding.

    The identification is positional: an operand of the band's first iteration
    that is produced outside the band, whose counterpart in the second iteration
    is produced inside it, is the same logical buffer as that counterpart.
    """
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)
    alias: dict[str, str] = {}
    for band in bands:
        if band.layer_count < 2:
            continue
        prefix = f"b{band.band_id}."
        first = _block_kernels(by_layer, band.first_layer, band.period)
        second = _block_kernels(
            by_layer, band.first_layer + band.period, band.period
        )
        for outer, inner in zip(first, second):
            for outside, inside in zip(outer.inputs, inner.inputs):
                here, later = keys.get(outside), keys.get(inside)
                if not here or not later:
                    continue
                if not later.startswith(prefix) or here.startswith(prefix):
                    continue
                if here.startswith("host."):
                    continue  # a host window is not a loop-carried buffer
                alias.setdefault(here, later)
    if not alias:
        return
    for name, key in list(keys.items()):
        target = alias.get(key)
        if target is not None:
            keys[name] = target


# -- states -----------------------------------------------------------------
def _place_states(
    graph: KernelGraph,
    bands: Sequence[LayerBand],
    band_of_kernel: Mapping[int, int],
    span_max: int,
) -> tuple[tuple[StatePlacement, ...], dict[str, list[Any]], list[str]]:
    """Merge each band's per-layer state resources into one physical resource.

    A 36-layer model declares 36 KV resources.  One layer loop cannot name 36
    static state descriptors, so the band's resources become one physical
    resource whose per-layer window is selected by the layer induction variable.
    Merging is legal only when the members agree on class, dtype, row width and
    capacity; otherwise they stay separate and the band degrades.
    """
    warnings: list[str] = []
    resources = {s.state_id: s for s in graph.states}
    by_index = {k.index: k for k in graph.kernels}

    # Which states does each *iteration* of each band touch, in kernel order?
    by_layer: dict[int, list[Kernel]] = {}
    for kernel in graph.kernels:
        if kernel.layer is not None:
            by_layer.setdefault(kernel.layer, []).append(kernel)
    band_states: dict[int, dict[int, list[str]]] = {}
    for band in bands:
        for iteration in range(band.layer_count):
            seen = band_states.setdefault(band.band_id, {}).setdefault(iteration, [])
            for layer in band.iteration_layers(iteration):
                for kernel in by_layer.get(layer, ()):
                    for name in (*kernel.state_reads, *kernel.state_writes):
                        if name not in seen:
                            seen.append(name)

    placements: list[StatePlacement] = []
    state_of_resource: dict[str, list[Any]] = {}
    claimed: set[str] = set()

    for band in bands:
        layer_map = band_states.get(band.band_id, {})
        iterations = list(range(band.layer_count))
        role_count = max((len(layer_map.get(i, [])) for i in iterations), default=0)
        for role in range(role_count):
            members: list[str] = []
            for iteration in iterations:
                names = layer_map.get(iteration, [])
                if role < len(names):
                    members.append(names[role])
            if not members:
                continue
            specs = {
                (
                    resources[m].state_class,
                    resources[m].dtype,
                    resources[m].row_elements,
                    _extent_value(resources[m].capacity_rows, span_max)[0],
                )
                for m in members
            }
            first = resources[members[0]]
            capacity = _extent_value(first.capacity_rows, span_max)[0]
            if len(specs) != 1:
                warnings.append(
                    f"band {band.band_id} role {role}: state resources disagree "
                    "on class, dtype, row width or capacity; they are placed "
                    "separately"
                )
                for member in members:
                    resource = resources[member]
                    cap = _extent_value(resource.capacity_rows, span_max)[0]
                    physical_id = f"state.{member}"
                    placements.append(
                        StatePlacement(
                            physical_id=physical_id,
                            state_class=resource.state_class,
                            members=(member,),
                            row_elements=resource.row_elements,
                            row_bytes=bytes_for(resource.row_elements, resource.dtype),
                            capacity_rows=cap,
                            dtype=resource.dtype,
                            band_id=band.band_id,
                        )
                    )
                    state_of_resource[member] = [physical_id, 0]
                    claimed.add(member)
                continue
            physical_id = f"state.b{band.band_id}.r{role}"
            placements.append(
                StatePlacement(
                    physical_id=physical_id,
                    state_class=first.state_class,
                    members=tuple(members),
                    row_elements=first.row_elements,
                    row_bytes=bytes_for(first.row_elements, first.dtype),
                    capacity_rows=capacity,
                    dtype=first.dtype,
                    band_id=band.band_id,
                )
            )
            for member_index, member in enumerate(members):
                state_of_resource[member] = [physical_id, member_index]
                claimed.add(member)

    for resource in graph.states:
        if resource.state_id in claimed:
            continue
        capacity = _extent_value(resource.capacity_rows, span_max)[0]
        physical_id = f"state.{resource.state_id}"
        placements.append(
            StatePlacement(
                physical_id=physical_id,
                state_class=resource.state_class,
                members=(resource.state_id,),
                row_elements=resource.row_elements,
                row_bytes=bytes_for(resource.row_elements, resource.dtype),
                capacity_rows=capacity,
                dtype=resource.dtype,
                band_id=None,
            )
        )
        state_of_resource[resource.state_id] = [physical_id, 0]
    placements.sort(key=lambda s: s.physical_id)
    return tuple(placements), state_of_resource, warnings


def _bind_state_tensors(
    graph: KernelGraph,
    tensors: Mapping[str, Tensor],
    state_of_resource: Mapping[str, Sequence[Any]],
) -> dict[str, list[Any]]:
    """Bind each state-role tensor to the physical resource it belongs to.

    A graph names its state effects on the kernel (``state_reads`` /
    ``state_writes``) and its state operands on the tensor, and the two need not
    use the same identifiers.  This pass joins them positionally at the point of
    declaration, so a later kernel that merely *reads* the tensor -- with no
    state effect of its own -- still resolves to the right resource.  A state
    tensor no kernel ever binds is not an error: it is a materialised view, and
    it is placed in an activation arena like any other intermediate.
    """
    # Several kernels may write disjoint planes of one fused state row -- a key
    # plane and a value plane of one KV row.  Each write therefore needs its own
    # column offset, accumulated in kernel order and wrapping when the row is
    # full; without it every plane would land at column zero and the last write
    # would erase the others.
    row_elements = {s.state_id: s.row_elements for s in graph.states}
    cursor: dict[str, int] = {}
    bound: dict[str, list[Any]] = {}
    for kernel in graph.kernels:
        writes = list(kernel.state_writes)
        reads = list(kernel.state_reads) or writes
        outs = [n for n in kernel.outputs if tensors[n].role == "state"]
        if not outs and writes:
            outs = list(kernel.outputs)
        for position, name in enumerate(outs):
            if not writes or name in bound:
                continue
            resource = writes[min(position, len(writes) - 1)]
            mapping = state_of_resource.get(resource)
            if mapping is None:
                continue
            width = 1
            for axis in tensors[name].shape[1:]:
                width *= max(_extent_value(axis, 1)[0], 1)
            row = int(row_elements.get(resource, 0))
            column = cursor.get(resource, 0)
            if row and column + width > row:
                column = 0
            bound[name] = [*mapping, column]
            cursor[resource] = column + width
        ins = [n for n in kernel.inputs if tensors[n].role == "state"]
        for position, name in enumerate(ins):
            if not reads or name in bound:
                continue
            mapping = state_of_resource.get(reads[min(position, len(reads) - 1)])
            if mapping is not None:
                bound[name] = list(mapping)
    for resource_id, mapping in state_of_resource.items():
        bound.setdefault(resource_id, list(mapping))
    return dict(sorted(bound.items()))


# -- kernels ----------------------------------------------------------------
#: Sub-case selectors that TA-ABI3-OPCONV-1 sections 3 and 12 put in ``aux0``
#: because several neutral kinds share one subopcode.
_SUBCASE: Mapping[str, int] = {
    "SCALE": 0,
    "MUL": 1,
    "SIGMOID": 2,
    "COMPRESS_PROJECT": 0,
    "COMPRESS_POOL": 1,
    "COMPRESS_STATE_UPDATE": 2,
    "HYPER_CONNECT_PRE": 0,
    "HYPER_CONNECT_POST": 1,
    "HYPER_CONNECT_HEAD": 2,
}

#: Subopcodes whose first operand is an index vector rather than a payload
#: (TA-ABI3-OPCONV-1 sections 2 and 7).
_INDEX_FIRST = {
    (int(Major.TENSOR), int(TensorOp.EMBED_LOOKUP)),
    (int(Major.DMA), int(Dma.GATHER)),
    (int(Major.DMA), int(Dma.SCATTER)),
}

#: Maximum input views TA-ABI3-OPCONV-1 allows per subopcode, where it is
#: tighter than the frozen record's four.  ``SILU_MUL`` is amendment A8: the
#: engine takes ``(gate, up)`` and refuses a third operand even though
#: ``KERNEL_TO_ENGINE`` gives ``SWIGLU`` an arity of three.
_MAX_INPUTS: Mapping[tuple[int, int], int] = {
    (int(Major.VECTOR), int(Vector.SILU_MUL)): 2,
    (int(Major.SELECTION), int(Selection.ARGMAX)): 1,
    (int(Major.SELECTION), int(Selection.TOKEN_APPEND)): 1,
}

_INDEX_DTYPES = frozenset({"u32", "i32", "u64", "i64"})


def _conforming_input_order(
    kernel: Kernel, engine: Any, tensors: Mapping[str, Tensor]
) -> tuple[list[int], list[int]]:
    """Return ``(ABI slot order, dropped IR slots)`` for one kernel's inputs.

    The neutral IR fixes *which* tensors an operation reads; TA-ABI3-OPCONV-1
    fixes *which slot* each one occupies.  Reconciling the two is the backend's
    job -- an engine rejects a non-conforming operator rather than guessing.
    """
    order = list(range(len(kernel.inputs)))
    key = (int(engine.family), int(engine.sub))
    if key in _INDEX_FIRST and len(order) >= 2:
        first = kernel.inputs[order[0]]
        if tensors[first].dtype not in _INDEX_DTYPES:
            for position, slot in enumerate(order):
                if tensors[kernel.inputs[slot]].dtype in _INDEX_DTYPES:
                    order.insert(0, order.pop(position))
                    break
    limit = _MAX_INPUTS.get(key, 4)
    dropped = order[limit:]
    return order[:limit], dropped


def _aux_ids(
    kernel: Kernel,
    engine: Any,
    tensors: Mapping[str, Tensor],
    graph: KernelGraph,
    span_max: int,
    groups: int,
) -> tuple[int, ...]:
    """Auxiliary IDs required by TA-ABI3-OPCONV-1 for this subopcode."""
    attributes = dict(kernel.attributes)
    family, sub = int(engine.family), int(engine.sub)
    aux: list[int] = []

    def out_cols(slot: int = 0) -> int:
        if slot >= len(kernel.outputs):
            return 0
        return matrix_shape(tensors[kernel.outputs[slot]], span_max)[1]

    def in_cols(slot: int) -> int:
        if slot >= len(kernel.inputs):
            return 0
        return matrix_shape(tensors[kernel.inputs[slot]], span_max)[1]

    if kernel.kind in _SUBCASE and family in (int(Major.VECTOR),):
        aux = [_SUBCASE[kernel.kind]]
    elif family == int(Major.ATTENTION):
        aux = [
            _group_size(kernel, tensors, attributes),
            int(attributes.get("mask_mode", 0 if attributes.get("causal", True) else 1)),
            int(Symbol.CONTEXT_LENGTH),
            int(Symbol.POSITION_START),
        ]
        if sub == int(Attention.SPARSE):
            aux[1] = int(attributes.get("block_width", 1))
    elif family == int(Major.ROUTE):
        if sub in (int(Route.TOPK), int(Route.BIASED_TOPK)):
            aux = [int(attributes.get("top_k", out_cols()))]
        elif sub == int(Route.EXPERT_DISPATCH):
            experts = attributes.get("expert_count")
            if experts is None:
                experts = _infer_expert_count(kernel, graph, tensors, span_max)
            if not experts:
                raise PlanError(
                    f"kernel {kernel.kernel_id}: EXPERT_DISPATCH requires an "
                    "expert bound in aux0 (TA-ABI3-OPCONV-1 section 5) and the "
                    "graph declares none; an unbounded expert ID is a memory "
                    "safety problem, not a routing detail"
                )
            aux = [int(experts)]
        elif sub == int(Route.INDEX_TOPK):
            aux = [
                int(attributes.get("top_k", out_cols())),
                int(attributes.get("mask_mode", 0)),
                int(Symbol.CONTEXT_LENGTH),
                int(Symbol.POSITION_START),
            ]
        elif sub == int(Route.WINDOW_INDEX):
            aux = [
                int(attributes.get("window", out_cols())),
                int(attributes.get("mask_mode", 0)),
                int(Symbol.CONTEXT_LENGTH),
            ]
    elif family == int(Major.TENSOR):
        if sub == int(TensorOp.GROUPED_MATMUL):
            aux = [
                int(attributes.get("group_count", 0))
                or _domain_extent(kernel, ("groups",), span_max)
                or groups
            ]
        elif sub == int(TensorOp.ROUTED_MATMUL):
            aux = [
                int(attributes.get("expert_count", 0))
                or _domain_extent(kernel, ("experts",), span_max)
                or groups
            ]
    elif family == int(Major.VECTOR):
        if sub == int(Vector.ROPE):
            aux = [int(attributes.get("rotary_width", in_cols(1)))]
        elif sub == int(Vector.HEAD_RMS_NORM):
            aux = [int(attributes.get("head_count", 1))]
        elif sub == int(Vector.SOFTMAX):
            aux = [int(attributes.get("axis", 1))]
        elif sub == int(Vector.HADAMARD):
            aux = [int(attributes.get("block_width", in_cols(0)))]
    return tuple(a for a in aux)


def _group_size(
    kernel: Kernel, tensors: Mapping[str, Tensor], attributes: Mapping[str, Any]
) -> int:
    """Query heads per key/value head, from the graph or from the operands.

    A grouped-query attention operator must state its group size: the engine
    checks it against the head counts it can see, and a wrong one silently
    pairs a query head with the wrong key head.  The graph usually names it;
    when it names it under its own spelling, the operand shapes still say it.
    """
    for key in ("group_size", "query_heads_per_key_value_head", "group"):
        if key in attributes:
            return max(int(attributes[key]), 1)
    if len(kernel.inputs) >= 2:
        query = tensors[kernel.inputs[0]].shape
        key_shape = tensors[kernel.inputs[1]].shape
        if len(query) >= 3 and len(key_shape) >= 3:
            query_heads, _ = _extent_value(query[1], 1)
            key_heads, _ = _extent_value(key_shape[1], 1)
            if key_heads:
                return max(int(query_heads) // int(key_heads), 1)
    return 1


def _infer_expert_count(
    kernel: Kernel,
    graph: KernelGraph,
    tensors: Mapping[str, Tensor],
    span_max: int,
) -> int:
    """Derive the expert bound from the routed contraction in the same layer."""
    for peer in graph.kernels:
        if peer.layer != kernel.layer:
            continue
        if peer.kind not in {"ROUTED_MATMUL", "GROUPED_MATMUL"}:
            continue
        if len(peer.inputs) < 2:
            continue
        a_rows, a_cols, _ = matrix_shape(tensors[peer.inputs[0]], span_max)
        w_rows, w_cols, _ = matrix_shape(tensors[peer.inputs[1]], span_max)
        if a_cols and w_rows % a_cols == 0:
            return w_rows // a_cols
        if a_cols and w_cols % a_cols == 0:
            return w_cols // a_cols
    return 0


def _domain_extent(kernel: Kernel, keys: Sequence[str], span_max: int) -> int:
    """Read one iteration-domain extent, resolving a symbol to its maximum."""
    for key in keys:
        if key in kernel.iteration_domain:
            value, _ = _extent_value(kernel.iteration_domain[key], span_max)
            if value:
                return int(value)
    return 0


def _plan_kernels(
    graph: KernelGraph,
    tensors: Mapping[str, Tensor],
    placements: Sequence[WeightPlacement],
    activation_keys: Mapping[str, str],
    state_of_tensor: Mapping[str, Sequence[Any]],
    bands: Sequence[LayerBand],
    band_of_kernel: Mapping[int, int],
    body_position: Mapping[int, int],
    span_max: int,
    tile: TileConfig,
    block: int,
    node_count: int,
    capability: Capability,
) -> tuple[tuple[KernelPlan, ...], list[str]]:
    """Plan one engine operation per kernel.

    ADR-003 section 6.2 puts the tile mapping in the SCHEDULE descriptor, not in
    the program: a loop nest exists for work that genuinely varies -- layers,
    token blocks, experts, vocabulary partitions -- while the decomposition of
    one contraction into row, column and depth tiles is a property of *how* the
    engine runs it.  Making tiles program loops instead would retire hundreds of
    thousands of engine dispatches for one forward step, which is the shape of
    failure ABI 3.0 exists to remove.  So this planner emits one operator per
    kernel and records the tile shape, the bank mask and the port mask for the
    schedule descriptor to carry.
    """
    warnings: list[str] = []
    placement_by_tensor = {p.tensor_id: p for p in placements}
    plans: list[KernelPlan] = []
    # The emitted body is the *first iteration* of each band, which spans the
    # band's period rather than a single layer.
    emitted_layers = {
        layer for band in bands for layer in band.iteration_layers(0)
    }

    for kernel in graph.kernels:
        if kernel.layer is not None and kernel.layer not in emitted_layers:
            continue
        engine = engine_for(kernel.kind)
        if len(kernel.outputs) > 2:
            raise PlanError(
                f"kernel {kernel.kernel_id}: {len(kernel.outputs)} outputs exceed "
                "the frozen ABI 3.0 operator limit of two output views"
            )
        slot_order, dropped = _conforming_input_order(kernel, engine, tensors)
        if dropped:
            warnings.append(
                f"kernel {kernel.kernel_id}: operand(s) "
                f"{[kernel.inputs[s] for s in dropped]} are not in the "
                f"{Major(engine.family).name}.{int(engine.sub)} operand "
                "convention and are not emitted"
            )
        band_id = band_of_kernel.get(kernel.index)
        contraction = (
            engine.family == int(Major.TENSOR) and engine.sub in _CONTRACTION_SUBOPS
        )

        out_name = kernel.outputs[0] if kernel.outputs else None
        if out_name is not None:
            rows, cols, symbolic = matrix_shape(tensors[out_name], span_max)
        else:
            rows, cols, symbolic = 1, 1, False
        if symbolic:
            rows = round_up(rows, block)

        shard_columns = cols
        depth = 0
        groups = 1
        transposed = False
        if contraction and len(kernel.inputs) >= 2:
            a_rows, a_cols, _ = matrix_shape(tensors[kernel.inputs[0]], span_max)
            w_rows, w_cols, _ = matrix_shape(tensors[kernel.inputs[1]], span_max)
            # The iteration domain is the authority on contraction geometry when
            # the graph states it.  A grouped projection contracts one group's
            # reduction width at a time, so inferring the depth from the folded
            # operand width would be wrong by the group count.
            depth = _domain_extent(
                kernel, ("reduction_width", "reduction", "depth"), span_max
            ) or a_cols
            groups = (
                _domain_extent(kernel, ("groups",), span_max)
                or int(kernel.attributes.get("groups", 0) or 0)
                or 1
            )
            # TA-ABI3-OPCONV-1 section 2: in1 is n-major ``[N, K]``.  A
            # checkpoint that stores ``[K, N]`` is presented n-major by swapping
            # the view's strides -- a description, never a relayout pass.
            if w_cols == depth:
                transposed = False
                weight_rows = w_rows
            elif w_rows == depth:
                transposed = True
                weight_rows = w_cols
            elif depth and w_cols % depth == 0:
                transposed = False
                weight_rows = w_rows
                groups = max(groups, w_cols // depth)
            elif depth and w_rows % depth == 0:
                transposed = True
                weight_rows = w_cols
                groups = max(groups, w_rows // depth)
            else:
                raise PlanError(
                    f"kernel {kernel.kernel_id}: contraction operand shapes "
                    f"{(a_rows, a_cols)} and {(w_rows, w_cols)} do not share a "
                    "depth axis"
                )
            if groups == 1 and weight_rows != cols:
                warnings.append(
                    f"kernel {kernel.kernel_id}: weight declares {weight_rows} "
                    f"output rows but the result declares {cols} columns; the "
                    "result shape wins"
                )
            if node_count > 1 and cols % node_count == 0 and cols > node_count:
                shard_columns = cols // node_count
            elif node_count > 1:
                warnings.append(
                    f"kernel {kernel.kernel_id}: {cols} output columns are not "
                    f"divisible by {node_count} nodes; this contraction is "
                    "replicated instead of sharded"
                )

        # Tile shape for the SCHEDULE descriptor.  These are hardware tiles, not
        # program loops: the engine decomposes one operator this way and the
        # cycle model costs it from exactly these numbers.
        tile_rows = choose_tile(max(rows, 1), tile.rows) if not symbolic else tile.rows
        tile_cols = choose_tile(max(shard_columns, 1), tile.cols)
        tile_depth = choose_tile(depth, tile.depth) if depth else 0

        row_loop = None
        if symbolic:
            row_loop = LoopPlan(
                loop_key=f"k{kernel.index}.block",
                kind="row",
                trip=max(rows // block, 1),
                symbol="span_tokens",
                divisor=block,
            )

        operands: list[OperandPlan] = []
        for abi_slot, ir_slot in enumerate(slot_order):
            operands.append(
                _operand_plan(
                    abi_slot,
                    "in",
                    kernel.inputs[ir_slot],
                    tensors,
                    placement_by_tensor,
                    activation_keys,
                    state_of_tensor,
                    span_max,
                    contraction=contraction,
                    row_loop=row_loop is not None,
                    kernel_rows=rows,
                    block=block,
                    transposed=transposed,
                    node_count=node_count,
                    shard_columns=shard_columns,
                    sharded=shard_columns != cols,
                    depth=depth,
                )
            )
        for abi_slot, name in enumerate(kernel.outputs):
            operands.append(
                _operand_plan(
                    abi_slot,
                    "out",
                    name,
                    tensors,
                    placement_by_tensor,
                    activation_keys,
                    state_of_tensor,
                    span_max,
                    contraction=contraction,
                    row_loop=row_loop is not None,
                    kernel_rows=rows,
                    block=block,
                    transposed=transposed,
                    node_count=node_count,
                    shard_columns=shard_columns,
                    sharded=shard_columns != cols,
                    depth=depth,
                )
            )

        link_class = ""
        if node_count > 1:
            if kernel.kind in LINK_CLASS_BY_KIND:
                link_class = LINK_CLASS_BY_KIND[kernel.kind]
            elif contraction and shard_columns != cols:
                link_class = "activation_transfer"

        plans.append(
            KernelPlan(
                index=kernel.index,
                kernel_id=kernel.kernel_id,
                kind=kernel.kind,
                engine_family=int(engine.family),
                engine_sub=int(engine.sub),
                numeric_contract=canonical_contract_id(kernel.numeric_contract),
                band_id=band_id,
                layer=kernel.layer,
                body_position=body_position.get(kernel.index, -1),
                contraction=contraction,
                block_rows=block,
                tile_rows=tile_rows,
                tile_cols=tile_cols,
                tile_depth=tile_depth,
                row_loop=row_loop,
                operands=tuple(operands),
                aux=_aux_ids(kernel, engine, tensors, graph, span_max, groups),
                slot_order=tuple(slot_order),
                groups=groups,
                phases=tuple(kernel.phases),
                link_class=link_class,
                shard_columns=shard_columns,
                depth=depth,
            )
        )
    return tuple(plans), warnings


def _operand_plan(
    slot: int,
    direction: str,
    name: str,
    tensors: Mapping[str, Tensor],
    placement_by_tensor: Mapping[str, WeightPlacement],
    activation_keys: Mapping[str, str],
    state_of_tensor: Mapping[str, Sequence[Any]],
    span_max: int,
    *,
    contraction: bool,
    row_loop: bool,
    kernel_rows: int,
    block: int,
    transposed: bool,
    node_count: int,
    shard_columns: int,
    sharded: bool,
    depth: int,
) -> OperandPlan:
    tensor = tensors[name]
    rows, cols, symbolic = matrix_shape(tensor, span_max)
    if symbolic:
        rows = round_up(rows, block)
    placement = placement_by_tensor.get(name)
    if placement is not None:
        residence = "weight"
        key = placement.group_id
    elif name in state_of_tensor:
        residence = "state"
        key = name
    elif tensor.role in {"input", "output"}:
        residence = "host"
        key = activation_keys.get(name, f"host.{direction}.{name}")
    else:
        residence = "arena"
        key = activation_keys.get(name, f"orphan.{name}")

    terms: list[str] = []
    view_rows, view_cols = rows, cols
    if contraction and direction == "in" and slot == 1:
        # in1 is the weight, presented n-major as ``[N, K]``.
        view_rows = shard_columns
        view_cols = depth or cols
        if placement is not None and placement.layer_stride_elements:
            terms.append("layer")
        if sharded:
            terms.append("node")
    elif contraction and direction == "out" and slot == 0:
        view_cols = shard_columns
        if row_loop:
            view_rows = block
            terms.append("row")
        if sharded:
            terms.append("node")
    else:
        if placement is not None and placement.layer_stride_elements:
            terms.append("layer")
        if row_loop and symbolic and rows == kernel_rows:
            # Only an operand whose position axis is the *kernel's* position
            # axis steps with the token-block loop.  An operand bounded by a
            # different symbol -- a sparse index count, say -- is presented
            # whole, because the loop's trip count is not its trip count.
            view_rows = block
            terms.append("row")
    return OperandPlan(
        slot=slot,
        direction=direction,
        tensor_id=name,
        residence=residence,
        key=key,
        dtype=tensor.dtype,
        rows=rows,
        cols=cols,
        tile_rows=max(view_rows, 1),
        tile_cols=max(view_cols, 1),
        transposed=transposed and contraction and direction == "in" and slot == 1,
        terms=tuple(terms),
    )


# -- SRAM -------------------------------------------------------------------
def _allocate_sram(
    kernels: Sequence[KernelPlan],
    capability: Capability,
    node_count: int,
    tile: TileConfig,
) -> tuple[SramRegion, ...]:
    """Allocate and bank-assign the explicitly managed scratchpad."""
    sram = capability.memory["sram"]
    total = int(sram["bytes"])
    banks = int(sram["banks"])
    bank_bytes = int(sram.get("bank_bytes", total // max(banks, 1)))
    ports = int(sram.get("ports", 1))

    max_rows = max((k.tile_rows for k in kernels), default=tile.rows)
    max_cols = max((k.tile_cols for k in kernels if k.contraction), default=tile.cols)
    max_depth = max((k.tile_depth for k in kernels if k.contraction), default=tile.depth)
    max_width = max(
        (o.tile_cols for k in kernels for o in k.operands), default=tile.cols
    )
    stream_width = min(max_width, 2048)

    requests: list[tuple[str, str, int, int, str, str]] = [
        # region_id, purpose, elements, element bytes, dtype, lifetime
        (
            "sram.activation_stage",
            "staged activation tile",
            max_rows * max_depth,
            2,
            "bf16",
            "per_depth_tile",
        ),
        (
            "sram.weight_stage",
            "staged weight tile (double buffered)",
            2 * max_depth * max_cols,
            2,
            "bf16",
            "per_depth_tile",
        ),
        (
            "sram.accumulator",
            "FP32 output tile accumulator",
            max_rows * max_cols,
            4,
            "fp32",
            "per_column_tile",
        ),
        (
            "sram.vector_stream",
            "vector engine streaming window",
            max_rows * stream_width,
            4,
            "fp32",
            "per_row_tile",
        ),
        (
            "sram.attention_working",
            "attention score and softmax working set",
            max_rows * stream_width,
            4,
            "fp32",
            "per_row_tile",
        ),
        (
            "sram.route_index",
            "route and expert index buffer",
            max_rows * int(capability.limits["max_topk"]) * 2,
            4,
            "u32",
            "per_row_tile",
        ),
        (
            "sram.state_stage",
            "transactional state prepare staging",
            max_rows * stream_width,
            2,
            "bf16",
            "per_transaction",
        ),
    ]
    if node_count > 1:
        chunk = int(capability.link.get("chunk_bytes", 1 << 16))
        channels = int(capability.link.get("virtual_channels", 1))
        requests.append(
            (
                "sram.link_stage",
                "inter-chip packetisation staging",
                chunk * channels // 2,
                2,
                "bf16",
                "per_collective",
            )
        )

    regions: list[SramRegion] = []
    cursor = 0
    bank_cursor = 0
    for region_id, purpose, elements, element_bytes, dtype, lifetime in requests:
        size = max(elements * element_bytes, bank_bytes)
        size = round_up(size, bank_bytes)
        bank_count = size // bank_bytes
        if bank_cursor + bank_count > banks or cursor + size > total:
            raise PlanError(
                f"SRAM region {region_id} needs {size} bytes in {bank_count} "
                f"banks; only {banks - bank_cursor} banks and "
                f"{total - cursor} bytes remain"
            )
        mask = ((1 << bank_count) - 1) << bank_cursor
        regions.append(
            SramRegion(
                region_id=region_id,
                purpose=purpose,
                offset=cursor,
                size_bytes=size,
                elements=size // element_bytes,
                dtype=dtype,
                bank_first=bank_cursor,
                bank_count=bank_count,
                bank_mask=mask,
                port_mask=(1 << ports) - 1,
                lifetime=lifetime,
            )
        )
        cursor += size
        bank_cursor += bank_count
    return tuple(regions)


# -- HBM address space ------------------------------------------------------
def _allocate_hbm(
    capability: Capability,
    groups: Sequence[WeightGroup],
    generated: Sequence[GeneratedConstant],
    states: Sequence[StatePlacement],
    arenas: Sequence[ArenaSlot],
    host_objects: Mapping[str, Mapping[str, Any]],
) -> dict[str, HbmPlacement]:
    """Assign every resident object a real base address and a home channel.

    A bump allocator over the node-local address space, in a fixed order, with
    each object aligned to its own natural alignment.  The home channel is the
    round robin over the declared channel count: the cycle model reads it to
    account request distribution, and an object that names no channel forces
    that model to invent one.

    Host-visible windows are allocated from a separate space, because they are
    not node HBM and interleaving them into it would misreport occupancy.
    """
    channels = max(int(capability.memory["hbm"].get("channels", 1)), 1)
    out: dict[str, HbmPlacement] = {}
    cursor = 0
    index = 0

    def place(key: str, size: int, alignment_log2: int) -> None:
        nonlocal cursor, index
        alignment = 1 << alignment_log2
        base = round_up(cursor, alignment)
        out[key] = HbmPlacement(
            key=key,
            base_address=base,
            size_bytes=size,
            channel=index % channels,
            alignment_log2=alignment_log2,
        )
        cursor = base + size
        index += 1

    # Immutable first: weights and derived constants are resident for the life
    # of the deployment, so they never fragment the mutable region.
    for group in groups:
        place(f"weight.{group.group_id}", group.size_bytes, 12)
    for constant in generated:
        place(f"generated.{constant.tensor_id}", constant.size_bytes, 12)
    for state in states:
        place(f"state.{state.physical_id}.committed", state.size_bytes, 12)
        place(f"state.{state.physical_id}.prepared", state.size_bytes, 12)
    for slot in arenas:
        place(f"arena.{slot.slot_id}", slot.size_bytes, 12)

    host_cursor = 0
    host_index = 0
    for key in sorted(host_objects):
        size = int(host_objects[key]["size_bytes"])
        base = round_up(host_cursor, 4096)
        out[f"host.{key}"] = HbmPlacement(
            key=f"host.{key}",
            base_address=base,
            size_bytes=size,
            channel=host_index % channels,
            alignment_log2=12,
        )
        host_cursor = base + size
        host_index += 1
    return out


# -- proofs -----------------------------------------------------------------
def _prove(
    capability: Capability,
    groups: Sequence[WeightGroup],
    arenas: Sequence[ArenaSlot],
    sram_regions: Sequence[SramRegion],
    states: Sequence[StatePlacement],
    kernels: Sequence[KernelPlan],
    bands: Sequence[LayerBand],
    node_count: int,
    host_objects: Mapping[str, Mapping[str, Any]],
    hbm_map: Mapping[str, HbmPlacement],
) -> dict[str, Any]:
    weight_bytes = sum(g.size_bytes for g in groups)
    arena_bytes = sum(a.size_bytes for a in arenas)
    state_bytes = sum(s.size_bytes * 2 for s in states)  # committed + prepared
    host_bytes = sum(int(o["size_bytes"]) for o in host_objects.values())
    sram_bytes = sum(r.size_bytes for r in sram_regions)
    hbm_available = int(capability.memory["hbm"]["bytes"])
    sram_available = int(capability.memory["sram"]["bytes"])
    resident = weight_bytes // max(node_count, 1) + arena_bytes + state_bytes

    masks: list[int] = []
    overlap = False
    for region in sram_regions:
        for other in masks:
            if other & region.bank_mask:
                overlap = True
        masks.append(region.bank_mask)

    proved_layers = sum(b.layer_count * b.period for b in bands)
    return {
        "hbm_address_span": max(
            (p.base_address + p.size_bytes for p in hbm_map.values()
             if not p.key.startswith("host.")),
            default=0,
        ),
        "hbm_channels": int(capability.memory["hbm"].get("channels", 1)),
        "weight_bytes": weight_bytes,
        "weight_objects": len(groups),
        "weight_segments": sum(len(g.segments) for g in groups),
        "activation_arena_bytes": arena_bytes,
        "activation_arena_slots": len(arenas),
        "state_bytes": state_bytes,
        "host_bytes": host_bytes,
        "sram_bytes": sram_bytes,
        "sram_available": sram_available,
        "sram_fits": sram_bytes <= sram_available,
        "sram_banks_disjoint": not overlap,
        "hbm_bytes_per_node": resident,
        "hbm_available_per_node": hbm_available,
        "hbm_fits": resident <= hbm_available,
        "node_count": node_count,
        "token_block_rows": max((k.block_rows for k in kernels), default=0),
        "layers_covered": proved_layers,
        "bands": len(bands),
        "degraded_bands": sum(1 for b in bands if b.degraded),
        "kernels_planned": len(kernels),
        "max_loop_depth": max(
            (
                (1 if k.band_id is not None else 0) + (1 if k.row_loop else 0)
                for k in kernels
            ),
            default=0,
        ),
        "tile_mapping_in_schedule": True,
        "capability_loop_depth": int(capability.limits["max_loop_depth"]),
        "zero_copy_weights": True,
    }
