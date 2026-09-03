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

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Container, Mapping, Sequence

from compiler.ir.v3.kernel_ir import (
    Kernel,
    KernelGraph,
    Symbolic,
    Tensor,
    require_neutral,
)
from compiler.ir.v3.lowering import (
    ABSENT_OPERANDS,
    abi_input_slots as _shared_input_slots,
    engine_for,
)
from compiler.ir.v3.numeric import canonical_contract_id
from runtime.abi3.capability import Capability, canonical_json, digest_of
from runtime.abi3.constants import (
    Attention,
    Dma,
    DTYPE_BITS,
    DType,
    Major,
    NO_ID,
    Reduction,
    Route,
    Selection,
    Tensor as TensorOp,
    TopologyClass,
    Vector,
)
from runtime.abi3.descriptors import Comparison, Symbol

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

#: Neutral state classes whose ABI 3.0 representation is one persistent,
#: ordinary writable HBM buffer.  These are DeepSeek's streaming caches and
#: compressor history: their source semantics require an in-place update on
#: every token step and provide no rollback/retry contract.  Qwen's
#: ``kv_cache`` deliberately remains outside this set and keeps the existing
#: committed/prepared STATE transaction lowering.
DIRECT_BUFFER_STATE_CLASSES = frozenset(
    {"compressed_kv", "compressor_window", "kv_window"}
)


def is_direct_buffer_state(state_class: str) -> bool:
    """Whether ``state_class`` lowers to one ordinary writable HBM object."""

    return str(state_class) in DIRECT_BUFFER_STATE_CLASSES

#: Kernel kinds whose ABI operation contracts over a depth axis and therefore
#: gets the row / output-tile / depth-tile loop nest.
_CONTRACTION_SUBOPS = frozenset(
    {int(TensorOp.MATMUL), int(TensorOp.GROUPED_MATMUL), int(TensorOp.ROUTED_MATMUL)}
)

#: Kernel kinds that can anchor a distributed transfer.  Whether a particular
#: site actually gets the class is decided in :func:`_plan_kernels`, after the
#: placement is known.  A coefficient-table GATHER and a hyper-connection
#: EXPERT_REDUCE are node-local operations despite sharing an ABI subopcode with
#: genuinely distributed sparse and MoE work; assigning traffic from the name
#: alone was the source of the old ``replicated_link_sites`` fiction.
LINK_CLASS_BY_KIND: Mapping[str, str] = {
    "EXPERT_DISPATCH": "expert_dispatch",
    "ATTENTION_SPARSE": "sparse_gather",
    "EXPERT_REDUCE": "reduction",
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

    ``block`` is the number of tokens one iteration of the token loop covers.
    A tensor view's extents are static while the token count is a runtime
    symbol, so a request whose span is not a multiple of the block has a partial
    final iteration; the device bounds it from the loop's ``bound_symbol`` and
    ``bound_divisor``, which is what makes a block larger than one token exact.
    Without that bound the only correct block is one token, and a forward step
    then retires one engine dispatch per token per operation -- the same
    retired-work failure, in different clothes, that ABI 3.0 exists to remove.
    """

    rows: int = 64
    cols: int = 128
    depth: int = 128
    block: int = 512

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
    residency: str = "replicated"  # replicated | node_sharded | mixed
    # A cluster memory-object descriptor is symmetric: every node sees the
    # same object ID and the same local byte extent.  When complete
    # authenticated segments can be partitioned across nodes, these are the
    # node-local source maps for that one descriptor.  ``segments`` remains the
    # logical/global checkpoint inventory used to prove that every binding is
    # present exactly once.
    local_size_bytes: int = 0
    node_segments: tuple[tuple[PlacedSegment, ...], ...] = ()
    materialization: str = "replicated"  # replicated | node_sharded | mixed

    @property
    def materialized_size_bytes(self) -> int:
        """The bytes the symmetric object occupies in one node's HBM."""

        return self.local_size_bytes if self.node_segments else self.size_bytes

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "group_id": self.group_id,
            "path": self.path,
            "size_bytes": self.size_bytes,
            "file_start": self.file_start,
            "file_end": self.file_end,
            "segment_count": len(self.segments),
            "segments": [s.to_dict() for s in self.segments],
            "residency": self.residency,
        }
        if self.node_segments:
            body.update(
                {
                    "local_size_bytes": self.local_size_bytes,
                    "node_segments": [
                        {
                            "node_id": node_id,
                            "segments": [segment.to_dict() for segment in segments],
                        }
                        for node_id, segments in enumerate(self.node_segments)
                    ],
                    "materialization": self.materialization,
                }
            )
        return body


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
    residency: str = "replicated"
    shard_count: int = 1
    # ``residency`` describes how the emitted computation selects this tensor.
    # ``materialization`` says whether the local object already starts at that
    # node's selected slice.  A dense one-segment tensor cannot be split while
    # retaining its binding digest, so it remains replicated and keeps the
    # NODE_ID view term even when its computation is column-sharded.
    materialization: str = "replicated"

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
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
            "residency": self.residency,
            "shard_count": self.shard_count,
        }
        if self.materialization != "replicated":
            body["materialization"] = self.materialization
        return body


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
    #: The producer/consumer pipeline that reuses this fixed-address block.
    #: Empty on every ordinary full-span arena.
    rolling_group: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "size_bytes": self.size_bytes,
            "rows": self.rows,
            "cols": self.cols,
            "dtype": self.dtype,
            "symbolic_rows": self.symbolic_rows,
            "tenants": list(self.tenants),
            **({"rolling_group": self.rolling_group} if self.rolling_group else {}),
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
    #: The graph's initial value for every row of this resource.  It is part of
    #: a resource's identity, not decoration: two resources that agree on class,
    #: dtype, row and capacity but disagree on it -- DeepSeek's compressor keeps
    #: its pooled keys at zero and its pooled scores at negative infinity -- are
    #: different resources and may not share a descriptor.
    initialization: str = "zero"

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
            "initialization": self.initialization,
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
    kind: str  # layer | row | context | column | depth
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
    #: Leading expert extent of a routed weight bank, ``0`` for every other
    #: operand.  A bank is presented as ``[E, N, K]``: the engine resolves the
    #: runtime expert ID inside the view, so the expert is an addressing
    #: dimension and folding it into the rows loses 255 of 256 experts.
    bank: int = 0
    #: Node-local leading extent of an expert-sharded bank.  ``bank`` remains
    #: the graph's global expert count; this field says how many consecutive
    #: expert matrices this node owns.  Keeping both numbers is necessary to
    #: derive the NODE_ID stride without weakening the routed operator's global
    #: expert-ID bound.
    bank_shard: int = 0
    #: Amendment A18's affine function of the row loop's bound symbol, for an
    #: operand that carries the ``row`` term.  The default is A13 exactly --
    #: the symbol's own value, no bias -- and encodes as four zero fields, so
    #: an operand that needs nothing new is byte-identical to the same operand
    #: written before the amendment.
    extent_numerator: int = 1
    extent_unit: int = 1
    extent_bias: int = 0
    #: The declared axis a *context* loop resolves, or ``-1``.  An operand that
    #: has one declares A18 for that axis rather than for the token axis: the
    #: token axis is static under the per-token dispatch such an operand's
    #: kernel runs under, so there is nothing there for A18 to say, and the
    #: candidate axis is the one the request moves.
    context_axis: int = -1
    context_numerator: int = 1
    context_unit: int = 1
    context_bias: int = 0
    #: The tensor lives in one fixed-address block reused by a shared row loop.
    rolling: bool = False

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
            # Stated only where it exists.  The plan document is bound into the
            # deployment manifest by digest, so a field every operand carries
            # would rewrite every existing plan to say "not a bank".
            **({"bank": self.bank} if self.bank else {}),
            **({"bank_shard": self.bank_shard} if self.bank_shard else {}),
            # Same rule for A18: an operand whose extent is the symbol's own
            # value states nothing, so no pre-amendment plan digest moves.
            **(
                {
                    "extent_numerator": self.extent_numerator,
                    "extent_unit": self.extent_unit,
                    "extent_bias": self.extent_bias,
                }
                if (self.extent_numerator, self.extent_unit, self.extent_bias)
                != (1, 1, 0)
                else {}
            ),
            **({"rolling": True} if self.rolling else {}),
            # And for the context axis: stated only by an operand that has one,
            # so no plan written before the context loop existed moves.
            **(
                {
                    "context_axis": self.context_axis,
                    "context_numerator": self.context_numerator,
                    "context_unit": self.context_unit,
                    "context_bias": self.context_bias,
                }
                if self.context_axis >= 0
                else {}
            ),
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
    #: A loop whose only job is to resolve a context-sized axis.  It runs once
    #: over the whole declared capacity; the resolution it carries is the point
    #: of it, exactly as the token loop's is when a single block covers the
    #: span.  ``None`` on every kernel that has no such axis, which is all but
    #: one operator today.
    context_loop: LoopPlan | None
    operands: tuple[OperandPlan, ...]
    aux: tuple[int, ...]
    slot_order: tuple[int, ...]
    groups: int
    phases: tuple[str, ...]
    link_class: str
    shard_columns: int
    depth: int
    #: Consecutive kernels with the same non-empty ID execute inside one shared
    #: token-block loop. Empty on ordinary producer-then-consumer schedules.
    stream_group: str = ""

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
            **(
                {"context_loop": self.context_loop.to_dict()}
                if self.context_loop
                else {}
            ),
            "operands": [o.to_dict() for o in self.operands],
            "aux": list(self.aux),
            "slot_order": list(self.slot_order),
            "groups": self.groups,
            "phases": list(self.phases),
            "link_class": self.link_class,
            "shard_columns": self.shard_columns,
            "depth": self.depth,
            **({"stream_group": self.stream_group} if self.stream_group else {}),
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


@dataclass(frozen=True, slots=True)
class RequestExtent:
    """Amendment A18: an extent as ``numerator * S / unit + bias``.

    ``S`` is the token-block loop's bound symbol.  Every neutral extent this
    program declares is one of these over that one symbol, which is the whole
    argument A18 makes for coefficients on the view instead of eight more
    entries in the frozen A5 registry: ``span_groups_ratio4`` is not a symbol,
    it is ``SPAN_TOKENS / 4``, and the next model's ratio would need a ninth.
    """

    numerator: int = 1
    unit: int = 1
    bias: int = 0
    #: The A5 symbol the function reads.  The token-block loop is bound on
    #: ``span_tokens`` and every extent it resolves is a function of that; an
    #: axis the *context* sizes is a function of ``context_length``, and the
    #: two coincide only in prefill.  Consumed by the context loop, which is
    #: the only place a loop is bound on an axis's own symbol; the row path
    #: still resolves a context axis against the span, which is what it has
    #: always done and what the operands that path serves have been qualified
    #: against.
    symbol: str = "span_tokens"

    def step(self, block: int) -> int | None:
        """Elements of this axis one whole iteration of a block loop covers.

        ``None`` when the unit does not divide ``numerator * block``: one
        iteration is then not a whole number of this axis's elements, the term
        walks nothing, and the amendment says so rather than rounding.
        """
        scaled = int(self.numerator) * int(block)
        if self.unit <= 0 or scaled % self.unit:
            return None
        return max(scaled // self.unit, 1)


#: Neutral extent name -> its affine function of the token-block loop's bound
#: symbol.  The maxima the exporter declares are the check on this table rather
#: than a second source of truth for it: at ``S = 262,144`` every function here
#: reproduces the declared maximum exactly, which :func:`request_extent_of`
#: asserts on every tensor it reads.
#:
#: ``context_*`` names resolve against the *span* deliberately.  In prefill the
#: two coincide; in decode a compressed layer's join is a sum over two
#: different symbols, which wire format section 12.8 places outside the
#: amendment and which the unresolved names below therefore decline to state
#: rather than approximate.
#:
#: That paragraph described a gap, and the gap was reached: the ``attention_*``
#: entries here are the *prefill* forms of a sum that has no single A18 image,
#: and a decode step of DeepSeek's compressed layers binds the two symbols
#: apart.  They are still the prefill forms, but nothing takes them on trust
#: any more -- ``_check_join_extent`` derives every axis-0 join's output from
#: its operands and refuses a declaration that disagrees -- and the decode form
#: is derived per phase by :func:`join_extent_under` rather than named here,
#: because it is not one entry.
REQUEST_EXTENT: Mapping[str, RequestExtent] = {
    "span_tokens": RequestExtent(),
    "context_tokens": RequestExtent(symbol="context_length"),
    "context_length": RequestExtent(symbol="context_length"),
    "span_groups_ratio4": RequestExtent(unit=4),
    "span_groups_ratio128": RequestExtent(unit=128),
    "context_groups_ratio4": RequestExtent(unit=4, symbol="context_length"),
    "context_groups_ratio128": RequestExtent(unit=128, symbol="context_length"),
    # The joins.  A bias is a count the operand carries whatever the request
    # is -- a 128-row committed sliding window is present for a span of one --
    # so it is added after the division and is not part of the step.  This is
    # the row A13 could not state at all: a clamp only shortens, and these are
    # longer than the rows the request supplies.
    "attention_rows_window": RequestExtent(bias=128),
    "attention_rows_ratio4": RequestExtent(numerator=5, unit=4, bias=128),
    "attention_rows_ratio128": RequestExtent(numerator=129, unit=128, bias=128),
    "selected_rows_ratio128": RequestExtent(unit=128, bias=128),
}


#: Engine operators whose operand row states an axis the *context* sizes
#: beside one the span sizes.  ``VECTOR.INDEX_SCORE``'s scores are
#: ``[B, S, C]``: two request-determined extents on one view, which amendment
#: A18 deliberately does not admit -- it names one axis, resolved from one loop
#: term.  The resolution is a loop rather than a wider descriptor: a per-token
#: dispatch makes ``S`` a static one, leaving ``C`` as the only extent the
#: request moves, and a context loop that runs once carries its resolution.
#:
#: This is the set of operators reached so far, not a claim that no other
#: operator has the shape.  ``ROUTE.INDEX_TOPK`` and the compressed attention
#: join have it too and will name themselves when they are reached; adopting
#: them here, unreached, would change operands that are qualified today.
CONTEXT_LOOP_OPS: frozenset[tuple[int, int]] = frozenset(
    {(int(Major.VECTOR), int(Vector.INDEX_SCORE))}
)


def context_axis_of(
    tensor: Tensor, span_max: int
) -> tuple[int, RequestExtent] | None:
    """The axis of this operand the *context* sizes, if it has one.

    Derived from the declared shape, never from a name: an axis whose extent is
    a function of a symbol the token-block loop is not bound to is one that
    loop cannot resolve, whichever axis it is and whatever the model calls it.
    A tensor with more than one is refused rather than guessed at -- A18 names
    one axis and two would need two loops, which is a shape no operand in
    either released graph has.
    """
    found: tuple[int, RequestExtent] | None = None
    for axis, extent in enumerate(tensor.shape):
        if not isinstance(extent, Symbolic):
            continue
        base = REQUEST_EXTENT.get(extent.symbol)
        if base is None or base.symbol == "span_tokens":
            continue
        resolved = RequestExtent(
            numerator=base.numerator * max(int(extent.multiplier), 1),
            unit=base.unit,
            bias=base.bias,
            symbol=base.symbol,
        )
        if found is not None:
            raise PlanError(
                f"tensor {tensor.tensor_id!r} has two context-sized axes "
                f"({found[0]} and {axis}); amendment A18 names one axis per "
                "view and resolving two would need two loops"
            )
        found = (axis, resolved)
    return found


#: Amendment A3's frozen ``comparisons`` registry, as the exporter's
#: symbol-comparison grammar spells it.  ``"<symbol> <op> <integer>"`` is the
#: whole grammar; an operator outside this table is refused rather than guessed
#: at, because a predicate read wrongly is a predicate that silently enables or
#: disables an operator.
#:
#: Ported from ``compiler/backends/rom/common/program.py`` (commit 48cd6ed):
#: one convention, two backends, and a predicate is a property of the ABI
#: rather than of a target.
PREDICATE_COMPARISONS: Mapping[str, Comparison] = {
    "==": Comparison.EQ,
    "!=": Comparison.NE,
    "<": Comparison.LT,
    "<=": Comparison.LE,
    ">": Comparison.GT,
    ">=": Comparison.GE,
}


def rewrite_comparison(
    extent: RequestExtent, operator: str, immediate: int
) -> tuple[Comparison, int]:
    """State ``f(S) <op> K`` as a comparison on the bound symbol itself.

    A18 makes a declared axis an affine image of a registered symbol,
    ``numerator * S / unit + bias`` with the division flooring, and A3's
    ``COMPARE_SYMBOL`` compares the *symbol* against an immediate.  So a
    condition written over the derived name has to be moved onto the symbol,
    and moved **exactly**: ``span_groups_ratio128 > 0`` is ``S // 128 > 0`` is
    ``S >= 128``, not ``S > 0``.  Getting that wrong by one unit is the whole
    defect class this lowering exists to close -- a predicate that reads true
    where the source reads false issues the operator the source skips.

    Only ``numerator == 1`` is rewritten.  A numerator above one makes the
    image non-surjective and an equality over it names a set of symbol values
    no single comparison states; rather than approximate it, this refuses.
    """
    unit = max(int(extent.unit), 1)
    numerator = int(extent.numerator)
    bias = int(extent.bias)
    if numerator != 1:
        raise PlanError(
            f"predicate over an axis whose A18 numerator is {numerator}: a "
            "comparison on the derived value is not a comparison on the "
            "symbol, and this backend will not approximate one"
        )
    # ``S // unit <op> target`` with ``target = immediate - bias``.  ``S`` is a
    # count and is never negative, which is what makes each rewrite exact.
    target = int(immediate) - bias
    if operator == ">":
        return Comparison.GE, max(unit * (target + 1), 0)
    if operator == ">=":
        return Comparison.GE, max(unit * target, 0)
    if operator == "<":
        return Comparison.LT, max(unit * target, 0)
    if operator == "<=":
        return Comparison.LT, max(unit * (target + 1), 0)
    if unit == 1:
        return PREDICATE_COMPARISONS[operator], target
    raise PlanError(
        f"predicate {operator!r} against an axis in units of {unit}: an "
        "equality on a floored quotient names a range of symbol values and "
        "``COMPARE_SYMBOL`` states one comparison; this backend will not "
        "approximate it"
    )


#: The three request scalars ABI 3.0 section 12.2 relates:
#: ``CONTEXT_LENGTH == POSITION_START + SPAN_TOKENS``.  A graph that pins one
#: of them in a phase pins a second, which is what lets an extent that sums
#: over two symbols collapse onto one *per phase* with no backend inventing an
#: identity of its own.
#:
#: Ported from ``compiler/backends/rom/common/program.py``: one convention, two
#: backends.  A resource whose extent the two lanes disagree about is not one
#: resource, and this program has already shipped one such disagreement -- the
#: attention join, 137 rows on the ROM lane and 257 on this one, for the same
#: decode step of the same graph.
PHASE_SYMBOL_BY_NAME: Mapping[str, Symbol] = {
    "span_tokens": Symbol.SPAN_TOKENS,
    "position_start": Symbol.POSITION_START,
    "context_length": Symbol.CONTEXT_LENGTH,
}

#: A18 request-extent symbol name -> the frozen A5 symbol it reads.
EXTENT_SYMBOL: Mapping[str, Symbol] = {
    "span_tokens": Symbol.SPAN_TOKENS,
    "context_length": Symbol.CONTEXT_LENGTH,
    "position_start": Symbol.POSITION_START,
}


def evaluate_comparison(comparison: Comparison, value: int, immediate: int) -> bool:
    """A frozen A3 comparison against a symbol whose value is known.

    Used to *prove* that two alternative paths of one kernel cannot both issue:
    each path's condition is evaluated under the other phase's pinned symbols,
    and a path that could still fire there is refused rather than emitted.
    """
    if comparison is Comparison.EQ:
        return value == immediate
    if comparison is Comparison.NE:
        return value != immediate
    if comparison is Comparison.LT:
        return value < immediate
    if comparison is Comparison.LE:
        return value <= immediate
    if comparison is Comparison.GT:
        return value > immediate
    return value >= immediate


def phase_substitution(
    pinned: Mapping[str, Any], where: str
) -> tuple[dict[int, int], dict[int, tuple[int, int]]]:
    """``(constants, aliases)`` implied by one phase's pinned symbols."""
    constants: dict[int, int] = {}
    for name, value in dict(pinned).items():
        symbol = PHASE_SYMBOL_BY_NAME.get(str(name))
        if symbol is None:
            raise PlanError(
                f"{where}: phase binding names {name!r}, which is not one of "
                "the three request scalars section 12.2 relates"
            )
        constants[int(symbol)] = int(value)
    aliases: dict[int, tuple[int, int]] = {}
    if int(Symbol.CONTEXT_LENGTH) not in constants:
        start = constants.get(int(Symbol.POSITION_START))
        span = constants.get(int(Symbol.SPAN_TOKENS))
        if start is not None:
            aliases[int(Symbol.CONTEXT_LENGTH)] = (int(Symbol.SPAN_TOKENS), start)
        elif span is not None:
            aliases[int(Symbol.CONTEXT_LENGTH)] = (int(Symbol.POSITION_START), span)
    return constants, aliases


def join_extent_under(
    tensors: Mapping[str, Tensor],
    names: Sequence[str],
    axis: int,
    span_max: int,
    constants: Mapping[int, int],
    aliases: Mapping[int, tuple[int, int]],
) -> tuple[RequestExtent | None, int]:
    """:func:`join_extent`, evaluated under one phase's substitutions.

    A17 makes a join's output the sum of its inputs and A18 states an extent as
    an affine image of *one* symbol.  DeepSeek's compressed attention join is a
    sum over two -- ``span_tokens + 128 + context_length / ratio`` -- so the sum
    has no A18 image at all and the exporter's ``attention_rows_ratioN`` was
    taken on trust.  It was wrong: it names the *span's* group count, which is
    the context's only while the span is the context.

    Under a phase's substitutions the sum does collapse.  A symbol the phase
    pins folds into the bias; a symbol the phase makes an offset image of
    another is rewritten onto it only when the rewrite survives the floor, so a
    nonzero offset against a group axis is left alone rather than approximated.
    Terms are then combined only where the combination is exact:
    ``floor(a*S) + floor(b*S/u) == floor((a*u + b)*S/u)`` because the first term
    is a whole number of the symbol's units; two floored terms have no such
    identity and are refused.
    """
    symbol: str | None = None
    exact = 0
    floored: RequestExtent | None = None
    bias = 0
    for name in names:
        tensor = tensors[name]
        entry = tensor.shape[axis] if axis < len(tensor.shape) else None
        if not isinstance(entry, Symbolic):
            value, _ = _extent_value(entry if entry is not None else 1, span_max)
            bias += int(value)
            continue
        extent = request_extent_of(tensor, span_max)
        if extent is None or int(entry.multiplier or 1) != 1:
            raise PlanError(
                f"join operand {name!r} leads on axis {axis} with "
                f"{entry.symbol!r}, which this backend cannot state as an A18 "
                "affine image"
            )
        unit = max(int(extent.unit), 1)
        numerator = int(extent.numerator)
        bias += int(extent.bias)
        named = EXTENT_SYMBOL.get(extent.symbol)
        if named is None:
            raise PlanError(
                f"join operand {name!r} reads {extent.symbol!r}, which is not "
                "one of the frozen request scalars"
            )
        key = int(named)
        value = constants.get(key)
        if value is not None:
            bias += numerator * int(value) // unit
            continue
        alias = aliases.get(key)
        if alias is not None and (alias[1] == 0 or unit == 1):
            bias += numerator * int(alias[1]) // unit
            key = alias[0]
        name_of = Symbol(key).name.lower()
        if symbol is None:
            symbol = name_of
        elif symbol != name_of:
            raise PlanError(
                f"a join of operands over {symbol} and {name_of} has no single "
                "A18 extent in this phase; this backend refuses to invent one"
            )
        if unit == 1:
            exact += numerator
        elif floored is None:
            floored = RequestExtent(numerator=numerator, unit=unit, symbol=name_of)
        else:
            raise PlanError(
                "a join with two floored operand extents has no exact A18 sum; "
                "this backend refuses to round one"
            )
    if symbol is None:
        return None, bias
    if floored is None:
        return RequestExtent(numerator=exact, unit=1, bias=bias, symbol=symbol), 0
    unit = int(floored.unit)
    return (
        RequestExtent(
            numerator=exact * unit + int(floored.numerator),
            unit=unit,
            bias=bias,
            symbol=symbol,
        ),
        0,
    )


def substitute_condition(
    triple: tuple[Symbol, Comparison, int],
    constants: Mapping[int, int],
    aliases: Mapping[int, tuple[int, int]],
) -> tuple[Symbol, Comparison, int] | bool:
    """One ``COMPARE_SYMBOL`` triple under a phase's substitutions.

    ``S + offset <op> K`` is ``S <op> K - offset`` for every frozen comparison,
    which is why moving a *condition* across the section 12.2 relation is exact
    where moving an *extent* across it is not.
    """
    symbol, comparison, immediate = triple
    value = constants.get(int(symbol))
    if value is not None:
        return evaluate_comparison(comparison, int(value), int(immediate))
    alias = aliases.get(int(symbol))
    if alias is not None:
        return Symbol(alias[0]), comparison, int(immediate) - int(alias[1])
    return symbol, comparison, immediate


def symbol_condition(condition: str) -> tuple[Symbol, Comparison, int]:
    """Parse one declared condition into an A3 ``COMPARE_SYMBOL`` triple."""
    parts = str(condition).split()
    if len(parts) != 3 or parts[1] not in PREDICATE_COMPARISONS:
        raise PlanError(
            f"predicate condition {condition!r} is not the declared "
            "'<symbol> <comparison> <integer>' statement over a runtime "
            "symbol.  ABI 3.0's frozen predicate kinds state a comparison and "
            "nothing else: there is no arithmetic in a PREDICATE payload and "
            "in particular no modulus"
        )
    name, operator, literal = parts
    extent = REQUEST_EXTENT.get(name)
    if extent is None:
        raise PlanError(
            f"predicate condition {condition!r} names {name!r}, which is not "
            "a runtime symbol this backend resolves; an unrecognised name "
            "would silently predicate nothing"
        )
    try:
        immediate = int(literal)
    except ValueError:
        raise PlanError(
            f"predicate condition {condition!r} compares against {literal!r}, "
            "which is not an integer immediate"
        ) from None
    comparison, value = rewrite_comparison(extent, operator, immediate)
    return Symbol[extent.symbol.upper()], comparison, value


def predicate_conditions(graph: KernelGraph) -> tuple[
    dict[str, str], dict[str, dict[str, str]]
]:
    """``predicate_output`` value name -> the condition this target states.

    A kernel that computes a boolean names it in ``predicate_output`` and says
    what it means in ``predicate_condition``, one entry per phase.  No neutral
    kind produces a ``bool`` and ABI 3.0 has no operator that could write one,
    so the value itself cannot exist on the device: what a backend can do is
    state the *condition* the value stands for, and only where a frozen
    predicate kind states it.

    The released compressor's condition has two phases and only one of them is
    expressible.  Prefill is ``span_groups_ratioN > 0`` -- a comparison over a
    declared symbol, which ``COMPARE_SYMBOL`` states exactly.  Decode is
    ``(start_pos + 1) % ratio == 0``, and the frozen ``comparisons`` registry
    has no modulus, no masking and no arithmetic; ``BOOLEAN_OBJECT`` reads a
    *statically* indexed word, so it cannot read ``ring[start_pos]`` either.
    Inventing a predicate kind for it would be an ABI change and is not a
    backend's to make, so the decode form is recorded as unrepresentable and
    reported in the deployment notes rather than approximated.
    """
    values: dict[str, str] = {}
    refused_values: dict[str, dict[str, str]] = {}
    for kernel in graph.kernels:
        name = kernel.attributes.get("predicate_output")
        if not name:
            continue
        declared = kernel.attributes.get("predicate_condition")
        if declared is None:
            raise PlanError(
                f"kernel {kernel.kernel_id!r} declares predicate output "
                f"{name!r} and no ``predicate_condition``; a value no "
                "instruction can compute and no condition can state is a "
                "predicate a backend would have to guess"
            )
        forms = (
            {"": str(declared)}
            if isinstance(declared, str)
            else {str(k): str(v) for k, v in dict(declared).items()}
        )
        usable: dict[str, str] = {}
        refused: dict[str, str] = {}
        for phase, condition in forms.items():
            try:
                symbol_condition(condition)
            except PlanError as exc:
                refused[phase] = f"{condition} -- {exc}"
            else:
                usable[phase] = condition
        if not usable:
            raise PlanError(
                f"kernel {kernel.kernel_id!r} declares predicate output "
                f"{name!r} whose every phase is outside ABI 3.0's frozen "
                f"predicate kinds: {refused}"
            )
        order = [p for p in ("prefill", "", "decode") if p in usable]
        chosen = usable[order[0] if order else sorted(usable)[0]]
        if refused:
            refused_values[str(name)] = {
                "lowered": chosen,
                **{f"refused.{phase}": text for phase, text in refused.items()},
            }
        values[str(name)] = chosen
    return values, refused_values


def condition_of(conditions: Mapping[str, str], declared: str, where: str) -> str:
    """One declared predicate, as a condition over a runtime symbol."""
    if declared in conditions:
        return conditions[declared]
    if len(str(declared).split()) != 3:
        raise PlanError(
            f"{where}: predicate {declared!r} is neither a symbol comparison "
            "nor the ``predicate_output`` of a kernel in this graph; a "
            "predicate a backend cannot resolve is a predicate it would "
            "silently drop"
        )
    return str(declared)


def kernel_condition(
    conditions: Mapping[str, str], kernel: Kernel
) -> str | None:
    """The one condition under which this kernel's operator is issued."""
    declared: list[str] = []
    attribute = kernel.attributes.get("execution_predicate")
    if attribute:
        declared.append(str(attribute))
    conditional = kernel.attributes.get("conditional_outputs")
    if conditional:
        names = {str(v) for v in dict(conditional).values()}
        # ``COMPRESS_STATE_UPDATE`` is the one kernel that declares this, and
        # the exporter's reason is that the released ``Compressor.forward``
        # writes its raw window on every step, so only the two pooled results
        # are conditional.  On this ABI the raw window is not part of the
        # operator at all -- ``VECTOR.COMPRESS`` binds no STATE resource in
        # this sub-case and the engine says so -- so both of the operator's
        # declared outputs are the pooled ones, there is nothing
        # unconditional left for it to do, and the whole instruction carries
        # the predicate.  Checked rather than assumed: an unconditional output
        # beside a conditional one is refused, because ABI 3.0 has no
        # per-output predicate and half-lowering one would write a result the
        # source did not produce.
        if len(names) != 1 or len(conditional) != len(kernel.outputs):
            raise PlanError(
                f"kernel {kernel.kernel_id!r} declares {len(conditional)} "
                f"conditional outputs of {len(kernel.outputs)} on "
                f"{len(names)} distinct predicates; ABI 3.0 predicates an "
                "instruction, not an output, so only an operator whose every "
                "output is conditional on one value is expressible"
            )
        declared.append(next(iter(names)))
    resolved = {condition_of(conditions, d, kernel.kernel_id) for d in declared}
    if not resolved:
        return None
    if len(resolved) > 1:
        raise PlanError(
            f"kernel {kernel.kernel_id!r} names {len(resolved)} distinct "
            f"predicates {sorted(resolved)}; an ABI 3.0 instruction carries "
            "one ``predicate_id`` and there is no conjunction"
        )
    return next(iter(resolved))


def operand_present(
    conditions: Mapping[str, str], kernel: Kernel
) -> tuple[int, str] | None:
    """The operand slot that vanishes, and the condition that keeps it."""
    declared = kernel.attributes.get("operand_present_predicate")
    if not declared:
        return None
    entries = dict(declared)
    if len(entries) != 1:
        raise PlanError(
            f"kernel {kernel.kernel_id!r} names {len(entries)} operands whose "
            "presence the request decides; two independent operands need four "
            "alternative paths and ABI 3.0 gives an instruction one predicate, "
            "so this backend refuses rather than picking one"
        )
    slot, condition = next(iter(entries.items()))
    index = int(slot)
    if not 0 <= index < len(kernel.inputs):
        raise PlanError(
            f"kernel {kernel.kernel_id!r} names operand {index} as "
            f"conditionally present; it has {len(kernel.inputs)} inputs"
        )
    if kernel_condition(conditions, kernel) is not None:
        raise PlanError(
            f"kernel {kernel.kernel_id!r} is both predicated and names a "
            "conditionally present operand; that is four paths on one "
            "``predicate_id``"
        )
    return index, condition_of(conditions, str(condition), kernel.kernel_id)


def join_extent(
    tensors: Mapping[str, Tensor],
    names: Sequence[str],
    axis: int,
    span_max: int,
) -> tuple[RequestExtent | None, int]:
    """The join-axis extent of a set of operands, as one affine statement.

    Amendment A17 makes a join's output extent the sum of its inputs', so the
    reduced path of a conditionally present operand has an output that is the
    sum over the operands that remain.  Static extents add into the bias -- a
    128-row sliding window is there for a span of one -- and symbolic ones add
    their numerators.  Two symbolic operands counted in *different* units, or
    over different symbols, have no single affine image and are refused rather
    than approximated: the full attention join is exactly that case, which is
    why the exporter states its fused form itself and only the reduced one is
    derived here.
    """
    symbol: str | None = None
    unit = 1
    numerator = 0
    bias = 0
    for name in names:
        tensor = tensors[name]
        entry = tensor.shape[axis] if axis < len(tensor.shape) else None
        if not isinstance(entry, Symbolic):
            value, _ = _extent_value(entry if entry is not None else 1, span_max)
            bias += int(value)
            continue
        extent = request_extent_of(tensor, span_max)
        if extent is None or int(entry.multiplier or 1) != 1:
            raise PlanError(
                f"join operand {name!r} leads on axis {axis} with "
                f"{entry.symbol!r}, which this backend cannot state as an A18 "
                "affine image; the reduced path's extent would be a guess"
            )
        if symbol is None:
            symbol, unit = extent.symbol, int(extent.unit)
        elif (symbol, unit) != (extent.symbol, int(extent.unit)):
            raise PlanError(
                f"a join of operands counted in different units ({symbol}/"
                f"{unit} and {extent.symbol}/{extent.unit}) has no single A18 "
                "extent; this backend refuses to invent one"
            )
        numerator += int(extent.numerator)
        bias += int(extent.bias)
    if symbol is None:
        return None, bias
    return RequestExtent(numerator=numerator, unit=unit, bias=bias, symbol=symbol), 0


def request_extent_of(tensor: Tensor, span_max: int) -> RequestExtent | None:
    """The A18 function of the leading axis, or ``None`` if it has none.

    An unrecognised symbol returns ``None`` and the operand keeps its declared
    maximum, which is what this backend did for every extent before the
    amendment.  That is deliberate: a name whose function nobody has written
    down is not an invitation to guess one, and A18's own admission rule
    refuses a declaration no term can resolve.
    """
    if not tensor.shape or not isinstance(tensor.shape[0], Symbolic):
        return None
    lead = tensor.shape[0]
    base = REQUEST_EXTENT.get(lead.symbol)
    if base is None:
        return None
    extent = RequestExtent(
        numerator=base.numerator * max(int(lead.multiplier), 1),
        unit=base.unit,
        bias=base.bias,
        symbol=base.symbol,
    )
    declared = int(lead.maximum)
    if declared > 0:
        # The exporter's declared maximum is this function evaluated at the
        # capability's context bound.  A disagreement is a coefficient this
        # table has wrong, and computing a wrong extent silently is the exact
        # failure A18 exists to remove, so it is refused here.
        computed = extent.numerator * int(span_max) // extent.unit + extent.bias
        if computed != declared:
            raise PlanError(
                f"tensor {tensor.tensor_id!r} declares maximum {declared} for "
                f"{lead.symbol!r}, but amendment A18's function "
                f"{extent.numerator} * {span_max} / {extent.unit} + "
                f"{extent.bias} gives {computed}; one of the two is wrong and "
                "an extent that is silently wrong is what A18 exists to stop"
            )
    return extent


def is_row_gather(kernel: Kernel, tensors: Mapping[str, Tensor]) -> bool:
    """True when a movement gathers *within* each row rather than across rows.

    ``DMA.GATHER`` names rows: the index array selects whole rows of the source
    and the result is one row per index.  A router's weight gather is a
    different operation wearing the same name -- for every token it selects six
    of that token's own 256 expert scores -- and presenting it as a row gather
    reads the six expert IDs as row numbers, which the engine refuses the
    moment one exceeds the request's row count:

    ``DMA index view 907 names row 255, outside the 104 rows of the addressed view``

    The two are told apart by the operands and not by a name: a row gather's
    index is one-dimensional in the rows it selects, while this one's index
    leads with the *same* symbolic axis as its source.  A shared leading axis
    means the index is indexing the trailing one, and the way to say that with
    an operator that indexes rows is to dispatch one row at a time -- which is
    what the per-token loop below is for.
    """
    if kernel.kind != "GATHER" or len(kernel.inputs) < 2 or not kernel.outputs:
        return False
    source = tensors.get(kernel.inputs[0])
    index = tensors.get(kernel.inputs[1])
    if source is None or index is None:
        return False
    if len(source.shape) < 2 or len(index.shape) < 2:
        return False
    lead = source.shape[0]
    if not isinstance(lead, Symbolic) or not isinstance(index.shape[0], Symbolic):
        return False
    return index.shape[0].symbol == lead.symbol


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


def expert_bank_extent(kernel: Kernel, tensor: Tensor, span_max: int) -> int:
    """The leading expert extent of a routed weight bank, or ``0``.

    A routed contraction reads one weight operand holding every expert's
    matrix, and TA-ABI3-OPCONV-1 section 2 has the engine resolve the runtime
    expert ID inside that view.  The expert axis is therefore an addressing
    dimension, and the operand is ``[E, N, K]`` where every other contraction
    weight is ``[N, K]``.

    The bank is recognised from the data -- the kernel declares how many
    experts it selects among and the operand's own leading extent is that many
    -- rather than from the operator's name.  A name is not a shape.
    """
    declared = int(kernel.attributes.get("expert_count", 0) or 0)
    if declared <= 1 or len(tensor.shape) != 3:
        return 0
    leading, _ = _extent_value(tensor.shape[0], span_max)
    return declared if leading == declared else 0


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------
def build_plan(
    graph: KernelGraph | Mapping[str, Any] | str,
    capability: Capability,
    *,
    topology: TopologyClass | int | None = None,
    tile: TileConfig | None = None,
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
    # Unconditional, and it used to be optional. An IR gate a backend can skip
    # is advice rather than a gate: amendment A20 moved index_family's refusal
    # into neutral admission precisely so one rule covers both lanes, and a
    # `validate=False` here would have been the hole that rule falls through.
    # Nothing called it.
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
    # One token block for the whole plan: the arena padding, the loop divisor,
    # every row-tiled view, and the generated position range must agree on it.
    block = max(min(int(tile.block), span_max), 1)
    generated = _generated_constants(
        graph,
        int(capability.limits["max_context_positions"]),
        headroom=max(
            min(tile.block, round_up(span_max, tile.rows)),
            tile.rows,
            span_max,
            round_up(span_max, block),
        ),
    )
    for name in positions:
        warnings.append(
            f"input {name} is materialised from arange_u32_v1 and offset by "
            "POSITION_START; the request's position range is a bound symbol, "
            "not host data"
        )

    units, body_position, band_of_kernel = _emission_order(graph, bands)
    states, state_of_resource, warn_state = _place_states(
        graph, bands, band_of_kernel, span_max
    )
    warnings.extend(warn_state)
    state_of_tensor = _bind_state_tensors(graph, tensors, state_of_resource)
    stream_kernels, rolling_tensors = _streaming_schedule(
        graph, tensors, body_position, band_of_kernel, block
    )
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
        rolling_tensors,
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
        stream_kernels,
        rolling_tensors,
    )
    warnings.extend(warn_kernels)
    groups, placements = _assign_weight_residency(
        groups, placements, kernel_plans, node_count
    )
    groups, placements = _materialize_node_local_weights(
        graph, groups, placements, kernel_plans, node_count
    )

    sram_regions = _allocate_sram(kernel_plans, capability, node_count, tile)
    hbm_map = _allocate_hbm(
        capability, groups, generated, states, arena_slots, host_objects
    )

    link = dict(capability.link)
    topology_plan = TopologyPlan(
        topology_class=int(topology_class),
        node_count=node_count,
        shard_axis="hybrid_output_columns_experts" if node_count > 1 else "none",
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
        placements,
        generated,
        arena_slots,
        sram_regions,
        states,
        kernel_plans,
        bands,
        node_count,
        host_objects,
        hbm_map,
    )
    if not bool(proofs["hbm_fits"]):
        raise PlanError(
            "physical HBM plan requires "
            f"{proofs['hbm_bytes_per_node']} bytes per node, capability "
            f"provides {proofs['hbm_available_per_node']}"
        )
    if not bool(proofs["sram_fits"]):
        raise PlanError(
            f"physical SRAM plan requires {proofs['sram_bytes']} bytes per "
            f"node, capability provides {proofs['sram_available']}"
        )
    if not bool(proofs["sram_banks_disjoint"]):
        raise PlanError(
            "physical SRAM plan assigns overlapping bank masks to live regions"
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

    **A one-element index input is the same tensor with the span factored out.**
    Where one exporter declares ``[span_tokens]`` holding ``POSITION_START + i``,
    another declares ``[1]`` holding ``POSITION_START`` and lets the consumer
    add the row -- DeepSeek-V4-Flash's ``input.position_offset`` is the second
    form, read by its rotary gather, its KV append, its window index and its
    final-row select, which is precisely the set of positional selectors.  It is
    the range's base, so it is derived the same way: element zero of the arange,
    offset by ``POSITION_START``.  Leaving it declared meant a host window the
    driver has no permission to fill -- the position is a *request symbol*, and
    a host that wrote it would be supplying an operand -- so every KV append in
    the program addressed row zero, and the ``i32`` the exporter chose for it is
    not the ``U32`` an index view is.  Both defects are the same defect: the
    tensor was never host data.
    """
    consumers: dict[str, list[str]] = {}
    for kernel in graph.kernels:
        for name in kernel.inputs:
            consumers.setdefault(name, []).append(kernel.kind)
    out: list[str] = []
    for tensor in graph.tensors:
        if tensor.role != "input" or tensor.dtype not in {"u32", "i32"}:
            continue
        if len(tensor.shape) != 1:
            continue
        leading = tensor.shape[0]
        if not isinstance(leading, Symbolic) and int(leading) != 1:
            continue
        kinds = consumers.get(tensor.tensor_id, [])
        if not kinds or any(k == "EMBEDDING_LOOKUP" for k in kinds):
            continue  # the token stream, not a position range
        out.append(tensor.tensor_id)
    return tuple(sorted(out))


#: Synthetic tensor id prefixes for cache-row lookup tables.
RING_INDEX_PREFIX = "generated.ring_indices."
FLOOR_DIV_INDEX_PREFIX = "generated.floor_div_indices."

#: Destination-row maps a neutral ``cache_row`` attribute may name.  A map this
#: backend does not implement is a compile error rather than an identity: the
#: identity is itself one of the maps, so guessing it is indistinguishable from
#: implementing it.
CACHE_ROW_MAPS = frozenset(
    {
        "absolute_position",
        "absolute_position_mod_window",
        "completed_absolute_position_floor_div_ratio",
    }
)


def ring_modulus(kernel: Kernel) -> int:
    """The ring capacity this kernel's destination rows wrap at, or 0.

    ``absolute_position_mod_window`` is a ring of ``window_size`` rows.  The
    other two maps read the position range unchanged -- ``absolute_position``
    because that is what it says, and
    ``completed_absolute_position_floor_div_ratio`` because a compressed
    group's row *is* its group ordinal, counted from the start of the request.
    """
    declared = kernel.attributes.get("cache_row")
    if declared is None:
        return 0
    name = str(declared)
    if name not in CACHE_ROW_MAPS:
        raise PlanError(
            f"kernel {kernel.kernel_id}: destination-row map {name!r} is not "
            f"one of {', '.join(sorted(CACHE_ROW_MAPS))}; a map this backend "
            "does not implement must not be taken as the identity"
        )
    if name != "absolute_position_mod_window":
        return 0
    window = int(kernel.attributes.get("window_size", 0) or 0)
    if window <= 0:
        raise PlanError(
            f"kernel {kernel.kernel_id}: addresses a ring but declares "
            f"window_size {window}"
        )
    return window


def floor_divisor(kernel: Kernel) -> int:
    """The divisor for a compressed-cache destination row, or zero.

    ABI 3.0 dynamic view terms can add a runtime position but cannot divide
    it.  A compressed append therefore indexes an immutable table containing
    ``position // ratio``.  The ratio is a property of the kernel and must be
    positive whenever this row map is selected.
    """

    declared = kernel.attributes.get("cache_row")
    if declared is None:
        return 0
    name = str(declared)
    if name not in CACHE_ROW_MAPS:
        raise PlanError(
            f"kernel {kernel.kernel_id}: destination-row map {name!r} is not "
            f"one of {', '.join(sorted(CACHE_ROW_MAPS))}; a map this backend "
            "does not implement must not be taken as the identity"
        )
    if name != "completed_absolute_position_floor_div_ratio":
        return 0
    divisor = int(kernel.attributes.get("ratio", 0) or 0)
    if divisor <= 0:
        raise PlanError(
            f"kernel {kernel.kernel_id}: compressed destination-row map "
            f"declares ratio {divisor}"
        )
    return divisor


def ring_moduli(graph: KernelGraph) -> set[int]:
    """Every distinct ring capacity the graph's cache writes address."""
    return {m for m in (ring_modulus(k) for k in graph.kernels) if m}


def floor_divisors(graph: KernelGraph) -> set[int]:
    """Every distinct compressed-cache divisor used by the graph."""

    return {d for d in (floor_divisor(k) for k in graph.kernels) if d}


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
    for modulus in sorted(ring_moduli(graph)):
        # A sliding-window KV cache holds the last ``modulus`` positions in a
        # ring, so absolute position ``p`` lives at row ``p % modulus``.  A
        # tensor view can offset an index vector by a runtime symbol but cannot
        # reduce one, so the reduction lives in the table: reading it at
        # ``POSITION_START + i`` yields ``(POSITION_START + i) % modulus`` with
        # no arithmetic in the descriptor.  The graph says which appends need
        # it, in ``cache_row``; ignoring that attribute made every window
        # append address an absolute position in a 128-row cache.
        count = max(int(context_max) + max(int(headroom), 1), 1)
        parameters = {"count": count, "modulus": int(modulus)}
        out.append(
            GeneratedConstant(
                tensor_id=f"{RING_INDEX_PREFIX}{int(modulus)}",
                generator="ring_indices_v1",
                parameters=parameters,
                size_bytes=int(generate("ring_indices_v1", parameters).nbytes),
                digest=digest_of("ring_indices_v1", parameters),
            )
        )
    for divisor in sorted(floor_divisors(graph)):
        # Reading element p returns floor(p / divisor).  Sampling this table
        # with an element stride of ``divisor`` also gives the consecutive
        # group ordinals needed by prefill, while a one-element decode view
        # gives the destination for the newly completed group.
        count = max(int(context_max) + max(int(headroom), 1), 1)
        parameters = {"count": count, "divisor": int(divisor)}
        out.append(
            GeneratedConstant(
                tensor_id=f"{FLOOR_DIV_INDEX_PREFIX}{int(divisor)}",
                generator="floor_div_indices_v1",
                parameters=parameters,
                size_bytes=int(generate("floor_div_indices_v1", parameters).nbytes),
                digest=digest_of("floor_div_indices_v1", parameters),
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
       takes is a zero-copy range rather than a gather across two.  A
       block-scaled role gets a *companion* object holding its scales in the
       same member order, because a block scale has no descriptor of its own
       and is addressed by the weight's offset divided by the block.
    2. one object per run of *file-adjacent* leftover bindings -- embeddings,
       final norms, the vocabulary projection -- so the object count stays in
       the low tens.

    No byte is copied, relaid out, or counted twice: every object's source is
    the ordered list of authenticated checkpoint ranges themselves.
    """
    tensors = {t.tensor_id: t for t in graph.tensors}

    def _segments(tensor: Tensor, cursor: int) -> list[PlacedSegment]:
        """The authenticated ranges one weight tensor contributes, in order.

        A binding is usually one range.  A *segmented* binding is a bank the
        model addresses as one operand and the checkpoint stores apart --
        DeepSeek's 256 routed experts per layer -- and contributes one range
        per segment, each with its own shard file, file offset and digest.

        Flattening it to ``(binding.path, binding.offset, binding.bytes)``
        balances byte for byte and names the wrong bytes: the experts are
        interleaved in the shard and not even ascending in it, so one 1 GiB
        range from expert 0 covers 255 other experts.  Every downstream total
        still reconciles, which is precisely why the expansion has to happen
        here, while the segments are still named.
        """
        binding = tensor.binding
        assert binding is not None
        if binding.transform != "identity":
            raise PlanError(
                f"tensor {tensor.tensor_id}: checkpoint binding declares "
                f"transform {binding.transform!r}; this backend never relayouts "
                "a weight image, so a non-identity transform must be resolved "
                "in the checkpoint lock"
            )
        placed: list[PlacedSegment] = []
        offset = cursor
        for source in binding.segments or (binding,):
            placed.append(
                PlacedSegment(
                    tensor_id=tensor.tensor_id,
                    source_name=source.source_name,
                    path=source.path,
                    file_offset=source.offset,
                    bytes=source.bytes,
                    sha256=source.sha256,
                    element_offset=elements_in(offset, tensor.dtype),
                    elements=elements_in(source.bytes, tensor.dtype),
                    dtype=tensor.dtype,
                )
            )
            offset += source.bytes
        return placed

    def _record(
        group_id: str,
        tensor_id: str,
        element_offset: int,
        layer: int | None,
        role_key: str,
        stride: int,
    ) -> WeightPlacement:
        """Where one *tensor* sits in its object.

        A placement is per tensor even when the payload arrives as many
        segments: a kernel names the tensor, and the whole tensor is what the
        view over it addresses.  The segments are the object's source, not its
        address space.
        """
        tensor = tensors[tensor_id]
        rows, cols, _ = matrix_shape(tensor, span_max)
        binding = tensor.binding
        assert binding is not None
        return WeightPlacement(
            tensor_id=tensor_id,
            group_id=group_id,
            element_offset=element_offset,
            elements=elements_in(binding.bytes, tensor.dtype),
            dtype=tensor.dtype,
            rows=rows,
            cols=cols,
            layer=layer,
            role_key=role_key,
            layer_stride_elements=stride,
        )

    weight_groups: list[WeightGroup] = []
    placements: list[WeightPlacement] = []
    placed: set[str] = set()

    def _group(group_id: str, members: Sequence[str], role_key: str) -> None:
        """Concatenate one ordered run of tensors into a single object."""
        segments: list[PlacedSegment] = []
        offsets: list[int] = []
        cursor = 0
        for member in members:
            tensor = tensors[member]
            offsets.append(elements_in(cursor, tensor.dtype))
            segments.extend(_segments(tensor, cursor))
            cursor += tensor.binding.bytes  # type: ignore[union-attr]
        stride = offsets[1] if len(offsets) > 1 else 0
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
        for layer_index, member in enumerate(members):
            placements.append(
                _record(
                    group_id,
                    member,
                    offsets[layer_index],
                    layer_index,
                    role_key,
                    stride,
                )
            )
            placed.add(member)

    def _scale_run(members: Sequence[str]) -> tuple[str, ...] | None:
        """The scale tensors of one weight role, in the role's own order.

        A block scale is not addressed by a descriptor of its own.  Amendments
        A8 and A15 state the code for element ``(row, col)`` as a position in
        the *weight's* own row-major space -- ``(row // scale_block_rows) *
        (cols // scale_block_elements) + col // scale_block_elements`` -- so
        the scale object's address space is the weight object's address space
        divided by the block, and nothing in the wire format can say otherwise.
        A role whose members are one tensor per layer therefore forces the
        layout of its scales exactly: concatenated in the same member order,
        because layer ``L`` sits at ``L * elements`` in the weight object and
        the block divides that offset into ``L * codes`` in the scale object.

        Left to the adjacency grouping below, the scales land in *file* order
        instead, which is neither the same origin nor the same stride.  The
        engine reads whatever code sits at the offset the weight implies: the
        first layer silently takes a neighbouring tensor's codes, and a later
        one walks off the end of the object.
        """
        run: list[str] = []
        for member in members:
            scale_id = tensors[member].scale_tensor_id
            if not scale_id:
                return None
            scale = tensors.get(scale_id)
            if scale is None or scale.binding is None or scale_id in placed:
                return None
            if scale_id in run:
                return None
            run.append(scale_id)
        return tuple(run) if run else None

    # (1) one object per weight role, segments in layer order -- and, for a
    # block-scaled role, one companion object holding its scales in the same
    # order, so that the weight object's address space divided by the block is
    # the scale object's.
    for role_key, members in weight_roles(graph, bands):
        _group(f"wr{len(weight_groups):04d}", members, role_key)
        scale_run = _scale_run(members)
        if scale_run is not None:
            _group(f"ws{len(weight_groups):04d}", scale_run, f"{role_key}.scale")

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
                "members": [],
            }
            runs.append(current)
        assert current is not None
        current["members"].append(
            (tensor.tensor_id, elements_in(current["cursor"], tensor.dtype))
        )
        current["segments"].extend(_segments(tensor, current["cursor"]))
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
        for tensor_id, element_offset in body["members"]:
            placements.append(_record(group_id, tensor_id, element_offset, None, "", 0))

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
            if tensors[name].role not in {"weight", "constant"}:
                continue
            seen: list[str] = []
            for block in blocks:
                peer = block[position]
                if slot >= len(peer.inputs):
                    return False, f"operand {position}.{slot} is missing in a block"
                if peer.inputs[slot] not in seen:
                    seen.append(peer.inputs[slot])
            if len(seen) == 1:
                # One tensor read by every iteration: stride zero.  Its address
                # does not move with the layer, so it needs no role object and
                # no checkpoint binding -- :func:`_place_weights` says so in the
                # same words.  A *generated* constant is exactly this case (the
                # rope coefficient table is one tensor for the whole stack), and
                # asking for its binding first refused a forty-layer band on the
                # one operand for which the question does not arise.
                continue
            if len(seen) != iterations:
                return False, (
                    f"operand {position}.{slot} is shared by some iterations and "
                    "private to others"
                )
            extents: set[tuple[int, str]] = set()
            for member_id in seen:
                member = tensors[member_id]
                if member.binding is None:
                    # A per-iteration payload really does need one: the role
                    # object's stride is the extent, and an unbound tensor
                    # states none.
                    return False, (
                        f"operand {position}.{slot} is private to each iteration "
                        "but has no checkpoint binding"
                    )
                extents.add((member.binding.bytes, member.dtype))
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


# -- bounded activation pipelines ------------------------------------------
def _streaming_schedule(
    graph: KernelGraph,
    tensors: Mapping[str, Tensor],
    body_position: Mapping[int, int],
    band_of_kernel: Mapping[int, int],
    block: int,
) -> tuple[dict[int, tuple[str, int]], dict[str, tuple[str, int]]]:
    """Find producer/consumer runs that may reuse one fixed-address block.

    A rolling arena is legal only when every consumer of the value executes in
    the same shared row loop as its producer.  Four released DeepSeek
    structures have that property and account for the maximum-context placement
    failure:

    * ``INDEX_SCORE`` immediately followed by the ``INDEX_TOPK`` that consumes
      its score plane, one query token at a time.  The score tensor has both a
      request-sized query axis and an independently request-sized candidate
      axis, while A18 can name only one dynamic extent on a view.  A one-row
      stream makes the query axis static and leaves the candidate axis as the
      one dynamic extent.  The joined window row carries the absolute prefill
      query position across that physical slice (A27); and
    * the query-B ``MATMUL -> HEAD_RMS_NORM -> ROPE`` chain, one ordinary token
      block at a time.  Only its first two intermediate values roll; the ROPE
      result remains full-span because sparse attention consumes it later; and
    * ``ATTENTION_SPARSE`` through the following ``HYPER_CONNECT_POST``, which
      keeps the wide attention/output-projection intermediates to one ordinary
      token block while retaining the final residual result; and
    * ``EXPERT_DISPATCH`` through the first following ``EXPERT_REDUCE`` in the
      same layer, one ordinary token block at a time.

    The recognition is structural and closed. A value with an external
    consumer stays full-span, and a group that crosses a layer/band boundary is
    refused by omission rather than guessed into a pipeline.
    """
    by_layer: dict[int | None, list[Kernel]] = {}
    for kernel in graph.kernels:
        by_layer.setdefault(kernel.layer, []).append(kernel)
    consumers: dict[str, list[int]] = {}
    for kernel in graph.kernels:
        for name in kernel.inputs:
            consumers.setdefault(name, []).append(kernel.index)
            scale = tensors[name].scale_tensor_id
            if scale:
                # A block-scaled operand consumes its scale view implicitly;
                # it is not a separate operator slot, but its lifetime and
                # rolling legality are the data operand's exactly.
                consumers.setdefault(scale, []).append(kernel.index)

    members: dict[int, tuple[str, int]] = {}

    def group_id(start: Kernel, end: Kernel, kind: str) -> str | None:
        start_band = band_of_kernel.get(start.index)
        if start_band != band_of_kernel.get(end.index):
            return None
        if start.layer != end.layer:
            return None
        if start_band is None:
            return f"k{start.index}.{kind}.{end.index}"
        return (
            f"b{start_band}.{kind}.p{body_position[start.index]}-"
            f"{body_position[end.index]}"
        )

    for layer, kernels in by_layer.items():
        if layer is None:
            continue
        for position, kernel in enumerate(kernels):
            if kernel.kind == "MATMUL" and position + 2 < len(kernels):
                middle = kernels[position + 1]
                end = kernels[position + 2]
                query_chain = (
                    middle.kind == "HEAD_RMS_NORM"
                    and end.kind == "ROPE"
                    and any(name in middle.inputs for name in kernel.outputs)
                    and any(name in end.inputs for name in middle.outputs)
                )
                if query_chain:
                    gid = group_id(kernel, end, "query_stream")
                    if gid is not None:
                        for member in (kernel, middle, end):
                            members[member.index] = (gid, block)
            if kernel.kind == "ATTENTION_SPARSE":
                end = next(
                    (
                        candidate
                        for candidate in kernels[position + 1 :]
                        if candidate.kind == "HYPER_CONNECT_POST"
                    ),
                    None,
                )
                if end is not None:
                    gid = group_id(kernel, end, "attention_output_stream")
                    if gid is not None:
                        end_position = kernels.index(end)
                        for member in kernels[position : end_position + 1]:
                            members[member.index] = (gid, block)
            if kernel.kind == "INDEX_SCORE" and position + 1 < len(kernels):
                end = kernels[position + 1]
                if end.kind != "INDEX_TOPK" or not any(
                    name in end.inputs for name in kernel.outputs
                ):
                    continue
                gid = group_id(kernel, end, "index_stream")
                if gid is None:
                    continue
                for member in (kernel, end):
                    members[member.index] = (gid, 1)
            if kernel.kind != "EXPERT_DISPATCH":
                continue
            end = next(
                (candidate for candidate in kernels[position + 1 :]
                 if candidate.kind == "EXPERT_REDUCE"),
                None,
            )
            if end is None:
                continue
            gid = group_id(kernel, end, "expert_stream")
            if gid is None:
                continue
            end_position = kernels.index(end)
            for member in kernels[position : end_position + 1]:
                members[member.index] = (gid, block)

    rolling: dict[str, tuple[str, int]] = {}
    for producer in graph.kernels:
        spec = members.get(producer.index)
        if spec is None:
            continue
        for name in producer.outputs:
            tensor = tensors[name]
            uses = consumers.get(name, ())
            if not uses or tensor.role in {"input", "output", "weight", "constant", "state"}:
                continue
            if all(members.get(index) == spec for index in uses):
                rolling[name] = spec
    return members, rolling


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
    rolling_tensors: Mapping[str, tuple[str, int]],
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
    sizes: dict[str, tuple[int, int, int, str, bool, str]] = {}
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
            rolling_group = ""
            rolling = rolling_tensors.get(name)
            if rolling is not None:
                rolling_group, rolling_block = rolling
                extent = request_extent_of(tensor, span_max)
                step = extent.step(rolling_block)
                if step is None:
                    raise PlanError(
                        f"rolling tensor {name!r} cannot form a whole row step "
                        f"from block {rolling_block}"
                    )
                rows = step + extent.bias
            elif symbolic:
                rows = round_up(rows, block)
            size = bytes_for(rows * cols, tensor.dtype)
            previous = sizes.get(key)
            if previous is None or size > previous[0]:
                sizes[key] = (
                    size, rows, cols, tensor.dtype, symbolic, rolling_group
                )
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
                rolling_group = ""
                rolling = rolling_tensors.get(name)
                if rolling is not None:
                    rolling_group, rolling_block = rolling
                    extent = request_extent_of(tensor, span_max)
                    step = extent.step(rolling_block)
                    if step is None:
                        raise PlanError(
                            f"rolling tensor {name!r} cannot form a whole row "
                            f"step from block {rolling_block}"
                        )
                    rows = step + extent.bias
                elif symbolic:
                    rows = round_up(rows, block)
                sizes[key] = (
                    bytes_for(rows * cols, tensor.dtype),
                    rows,
                    cols,
                    tensor.dtype,
                    symbolic,
                    rolling_group,
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
        size, rows, cols, dtype, symbolic, rolling_group = sizes[key]
        chosen = None
        # A rolling pipeline keeps one explicit buffer per value.  Reusing a
        # second stage's object merely because the liveness intervals do not
        # overlap would make two numerically distinct operand bindings collapse
        # to one descriptor under the shared edge loop, and it leaves no
        # physical separation for an asynchronous producer/consumer fence to
        # protect. The buffers are block-sized; clarity costs megabytes here,
        # while the eliminated full-context planes are tens of gigabytes.
        for slot in slots if reuse_arenas and not rolling_group else ():
            if (
                slot["size_bytes"] != size
                or slot["dtype"] != dtype
                or slot["rolling_group"] != rolling_group
            ):
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
                "rolling_group": rolling_group,
                "tenants": [],
                "free_at": 0,
            }
            slots.append(chosen)
        chosen["tenants"].append(key)
        chosen["free_at"] = max(chosen["free_at"], last_use.get(key, 0) + 1)
        arena_of_key[key] = chosen["slot_id"]

    for key in host_keys:
        size, rows, cols, dtype, symbolic, _rolling_group = sizes[key]
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
            rolling_group=slot["rolling_group"],
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
                    resources[m].initialization,
                )
                for m in members
            }
            first = resources[members[0]]
            capacity = _extent_value(first.capacity_rows, span_max)[0]
            if len(specs) != 1:
                warnings.append(
                    f"band {band.band_id} role {role}: state resources disagree "
                    "on class, dtype, row width, capacity or initial value; "
                    "they are placed separately"
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
                            initialization=resource.initialization,
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
                    initialization=first.initialization,
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
                initialization=resource.initialization,
            )
        )
        state_of_resource[resource.state_id] = [physical_id, 0]
    placements = _pool_states(placements, state_of_resource)
    placements.sort(key=lambda s: s.physical_id)
    return tuple(placements), state_of_resource, warnings


def _pool_states(
    placements: list[StatePlacement],
    state_of_resource: dict[str, list[Any]],
) -> list[StatePlacement]:
    """Pool one band's resources with the *other bands'* replicas of them.

    Merging per band answers "one loop body can name only one descriptor".  It
    does not answer "the sequencer holds a slot per declared resource for the
    life of a transaction", which is what ``max_state_resources`` bounds
    (amendment A22) and which counts descriptors across the whole deployment.
    DeepSeek-V4-Flash bands into a two-layer prologue, a single irregular layer
    and a forty-layer period-two body; the middle band's seven resources are
    replicas of seven of the body's, and kept apart they are nineteen
    descriptors against a sixteen-slot file, so the deployment is refused at
    admission.  The ROM backend compiles the same graph to ten because it groups
    by shape over the whole graph.

    What may share a descriptor is a *replica*: the same resource that several
    bands each hold their own copy of.  Two placements of one band are two roles
    the same iteration needs at once -- a key cache and a value cache -- and
    stay separate, so a pool holds at most one placement per band.  That is the
    conservative half of the rule and it is deliberate: one descriptor is one
    prepare, one commit, one cursor and one generation counter, and giving two
    independent resources one of each is a loss of meaning that the slot file
    does not ask for.

    Pooling is legal on the condition the per-band merge already uses -- the
    members agree on class, dtype, row width, capacity and initial value -- so
    the descriptor's window is the same size for every member and a member is
    selected by an element offset.  Each source placement's members stay
    contiguous and in order inside the pool, so a band's layer induction
    variable still walks its own members by adding one window per iteration to
    that placement's base.
    """
    pools: dict[tuple[Any, ...], list[StatePlacement]] = {}
    for placement in placements:
        key = (
            placement.state_class,
            placement.dtype,
            placement.row_elements,
            placement.row_bytes,
            placement.capacity_rows,
            placement.initialization,
        )
        pools.setdefault(key, []).append(placement)
    out: list[StatePlacement] = []
    for key in sorted(pools, key=lambda k: str(k)):
        group = sorted(pools[key], key=lambda p: p.physical_id)
        lanes: list[list[StatePlacement]] = []
        for placement in group:
            for lane in lanes:
                if all(held.band_id != placement.band_id for held in lane):
                    lane.append(placement)
                    break
            else:
                lanes.append([placement])
        merged = [lane for lane in lanes if len(lane) > 1]
        state_class, dtype, row_elements, row_bytes, capacity_rows, init = key
        base_id = (
            f"state.pool.{state_class}.{dtype}.r{row_elements}"
            f".c{capacity_rows}.{init}"
        )
        for index, lane in enumerate(lanes):
            if len(lane) == 1:
                # A lane nothing pooled with keeps its name, so a graph that
                # pools nothing produces the deployment it produced before.
                out.append(lane[0])
                continue
            physical_id = base_id if len(merged) == 1 else f"{base_id}.l{index}"
            members: list[str] = []
            for placement in lane:
                offset_base = len(members)
                for offset, member in enumerate(placement.members):
                    state_of_resource[member] = [physical_id, offset_base + offset]
                members.extend(placement.members)
            bands = {p.band_id for p in lane}
            out.append(
                StatePlacement(
                    physical_id=physical_id,
                    state_class=state_class,
                    members=tuple(members),
                    row_elements=row_elements,
                    row_bytes=row_bytes,
                    capacity_rows=capacity_rows,
                    dtype=dtype,
                    # A pool that spans bands belongs to no single one.
                    # Reporting one of them would name a band that does not own
                    # most of the members.
                    band_id=next(iter(bands)) if len(bands) == 1 else None,
                    initialization=init,
                )
            )
    return out


def writes_state_plane(
    kernel: Kernel,
    tensors: Mapping[str, Tensor],
    name: str,
    value_reads: Container[str],
) -> bool:
    """Is this output of a state-writing kernel *the resource*, or a value?

    A kernel that declares a state effect does not thereby make every result it
    produces a plane of that resource.  ``DMA.CACHE_APPEND``'s destination is
    the cache and Qwen declares it ``role: activation``, so the role alone
    cannot decide it.  ``VECTOR.COMPRESS``'s state-update sub-case is the
    counter-example: it rolls the compressor's raw window -- a real state
    effect, and one the operand convention binds to no operand at all -- while
    its two results are the pool operands ``COMPRESS_POOL`` reads next.

    The graph already separates them.  A resource plane is written and not read
    again as an operand; a value is produced to be consumed.  Routing a
    consumed value into the state image writes it to a different object from
    the one its reader addresses, and the reader gets whatever the resource
    held.
    """
    if not kernel.state_writes:
        return False
    if tensors[name].role == "state":
        return True
    return name not in value_reads


def value_reads(graph: KernelGraph) -> frozenset[str]:
    """Tensors some kernel reads as an ordinary operand."""
    return frozenset(name for kernel in graph.kernels for name in kernel.inputs)


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
    consumed = value_reads(graph)
    for kernel in graph.kernels:
        writes = list(kernel.state_writes)
        reads = list(kernel.state_reads) or writes
        outs = [n for n in kernel.outputs if tensors[n].role == "state"]
        if not outs and writes:
            outs = [
                n
                for n in kernel.outputs
                if writes_state_plane(kernel, tensors, n, consumed)
            ]
        for position, name in enumerate(outs):
            if name in bound:
                continue
            if kernel.kind == "STATE_READ":
                # A STATE_READ creates no plane: it re-presents the state view
                # supplied as its input with a narrower valid-row extent.  Keep
                # the complete binding, including a fused row's column, rather
                # than allocating the result in an activation arena.  The
                # latter can legally reuse the producer's old buffer and turn
                # a state read into a stale-activation read with no trap.
                source = (
                    kernel.inputs[min(position, len(kernel.inputs) - 1)]
                    if kernel.inputs
                    else ""
                )
                inherited = bound.get(source)
                if inherited is not None:
                    bound[name] = list(inherited)
                    continue
                if not reads:
                    continue
                mapping = state_of_resource.get(
                    reads[min(position, len(reads) - 1)]
                )
                if mapping is not None:
                    bound[name] = list(mapping)
                continue
            if not writes:
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
    # TA-ABI3-OPCONV-1 section 5: ``ROUTE.EXPERT_DISPATCH`` reads the expert
    # IDs in ``in0`` and the tokens in ``in1``.  Both exporters emit
    # ``(tokens, ids)`` -- the released module's own argument order -- so
    # without this the engine reads the activations as U32 expert IDs.
    (int(Major.ROUTE), int(Route.EXPERT_DISPATCH)),
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

#: Neutral operand orders that differ from TA-ABI3-OPCONV-1's slot order, and
#: the permutation that reconciles them.  Section 3's ``MHC`` row is
#: ``(hidden, fn, base, scale)``; both exporters emit
#: ``(hidden, fn, scale, base)``, following the released module's own argument
#: order.  The neutral IR fixes *which* tensors an operation reads and the
#: convention fixes *which slot* each occupies, so the reconciliation belongs
#: here -- the same reasoning as amendment A11's ``KV_APPEND`` permutation, and
#: the same reason ADR-003 section 15 keeps a backend concern out of the IR.
_SLOT_PERMUTATION: Mapping[str, tuple[int, ...]] = {
    "HYPER_CONNECT_PRE": (0, 1, 3, 2),
    "HYPER_CONNECT_HEAD": (0, 1, 3, 2),
}

#: ABI input slots this backend supplies ``absent_operands`` for, by neutral
#: kind, because the operand convention requires them empty and no exporter can
#: yet say so.  ``VECTOR.COMPRESS`` sub-case 2 is the only case: its ``in1`` is
#: the projection matrix, which a state update has none of, while its ``in2``
#: is the position embedding -- exactly what the APE table is.
#:
#: This is *not* a second hole table.  Amendment A20 makes ``absent_operands``
#: the one statement of a hole and
#: ``compiler/ir/v3/lowering.py::abi_input_slots`` the one placement of it, and
#: both are adopted below; what survives here is a seed for that call, because
#: ``COMPRESS_STATE_UPDATE`` is not in the frozen ``OPTIONAL_INPUT_SLOTS`` and
#: a kernel that declared the attribute would be refused at neutral admission.
#: Adding it there, and emitting it from the exporters, deletes this table
#: outright and changes nothing else -- the placement is already shared.
#: ``compiler/backends/rom/common/program.py`` seeds the same row for the same
#: reason: one convention, two backends.
_CONVENTION_EMPTY_INPUT_SLOTS: Mapping[str, tuple[int, ...]] = {
    "COMPRESS_STATE_UPDATE": (1,),
}


def _hole_attributes(kernel: Kernel) -> Mapping[str, object]:
    """``kernel.attributes``, with the convention's own holes seeded in.

    A kernel that declares ``absent_operands`` has already been checked against
    the frozen ``OPTIONAL_INPUT_SLOTS`` at neutral admission and is authoritative
    -- the backend adds nothing to it.
    """
    if ABSENT_OPERANDS in kernel.attributes:
        return kernel.attributes
    convention = _CONVENTION_EMPTY_INPUT_SLOTS.get(kernel.kind)
    if convention is None:
        return kernel.attributes
    return {**kernel.attributes, ABSENT_OPERANDS: list(convention)}


def _declared_holes(kernel: Kernel) -> tuple[int, ...]:
    """The ABI input slots the *graph* states this kernel leaves ``NO_ID``.

    The graph's own declaration only, never the convention seed above: the
    frozen ``check_operand_slots`` counts a declared hole against the kind's
    arity in ``KERNEL_TO_ENGINE``, so a slot the table has already admitted is
    a slot the table has room for.  ``COMPRESS_STATE_UPDATE``'s row has two
    inputs and uses ``in0`` and ``in2``, so its hole is a third slot the arity
    does not count -- which is one of the reasons it cannot yet be spelled as
    ``absent_operands``, and the reason it is not counted here.
    """
    declared = kernel.attributes.get(ABSENT_OPERANDS) or ()
    return tuple(int(slot) for slot in declared)  # type: ignore[union-attr]


def _abi_input_slots(kernel: Kernel, order: Sequence[int]) -> list[int | None]:
    """The IR input each ABI input slot carries; ``None`` for a declared hole.

    Amendment A20: the placement is
    ``compiler/ir/v3/lowering.py::abi_input_slots`` and nothing else, so a hole
    is placed identically on both lanes rather than by two private copies of
    one while-loop.  The operands go *either side* of the hole and are never
    packed down: ``ROUTE.INDEX_TOPK``'s dense form leaves ``in0`` empty and
    keeps the window block in ``in1`` and the compression ratio in ``in2``, and
    a backend that packed them down would hand the engine the one-element ratio
    constant where the window block belongs -- which is exactly what the engine
    then said, ``ROUTE.INDEX_TOPK window view 2084 covers 1 query rows,
    expected 104``.
    """
    base = _expert_sum_base(kernel)
    if base is not None:
        # TA-ABI3-OPCONV-1 section 6 reads (contributions, weights, base) and
        # amendment A10 makes the weights optional: a graph that names a base
        # operand has already applied its weights, and the released expert
        # multiplies by the routing weight before its down projection, so
        # re-applying them at the reduction would square them.  Packing the
        # operands down put the base where the weights belong and the engine
        # said so exactly -- ``EXPERT_SUM weight view holds 4,096 weights for 6
        # contributions``.  Everything else the kernel reads, the routed rows'
        # expert identity among it, is a dataflow fact this row has no slot
        # for, so it is dropped rather than left to occupy the base slot with
        # 32-bit integers.  This hole is *derived* from an attribute naming an
        # operand rather than declared as a slot, so it is not an
        # ``absent_operands`` statement and is not spelled as one.
        # ``compiler/backends/rom/common/program.py``'s ``_expert_sum_slots``
        # states the same convention: one convention, two backends.
        return [0, None, base]
    return _shared_input_slots(kernel.kind, list(order), _hole_attributes(kernel))


def _expert_sum_base(kernel: Kernel) -> int | None:
    """The IR input holding an expert reduction's base, when the graph names one."""
    if kernel.kind != "EXPERT_REDUCE":
        return None
    declared = kernel.attributes.get("base_operand_index")
    if declared is None:
        return None
    index = int(declared)
    if not 0 < index < len(kernel.inputs):
        raise PlanError(
            f"kernel {kernel.kernel_id}: base_operand_index {index} names no "
            f"input of the {len(kernel.inputs)} this kernel reads"
        )
    return index


#: Trailing input slots TA-ABI3-OPCONV-1 leaves optional, by neutral kind.
#: Everything not named here must fill every slot its engine row declares.
#: The numbers come from the engines themselves: a slot read through
#: ``optional_input`` is optional and a slot read through ``input_view`` is
#: not, and they are trailing in every case, which is what lets one integer
#: state it.
_OPTIONAL_INPUTS: Mapping[str, int] = {
    # REDUCTION.GROUPED_CONCAT joins one to four sources.
    "CONCAT": 3,
    # A10 makes the routing weight optional (it may be applied earlier), and
    # the shared-expert base has always been.
    "EXPERT_REDUCE": 2,
    "ORDERED_SUM": 1,
    "PARTITION_SUM": 1,
    # ROUTED_MATMUL's routing weights; the expert IDs in in2 are not optional.
    "ROUTED_MATMUL": 1,
    # The carried plane of a *partial* dequantisation.
    "DEQUANTIZE": 1,
    # The unweighted DeepSeek head norm passes no gain vector.
    "HEAD_RMS_NORM": 1,
    # VECTOR.SCALE sub-case 0 takes its constant from the numeric profile.
    "SCALE": 1,
    # The dense and grouped attention mask, and the sparse index and sink
    # arrays, which amendment A6 nonetheless requires for SPARSE.
    "ATTENTION_DENSE": 1,
    "ATTENTION_GQA": 1,
    "ATTENTION_SPARSE": 2,
}


def _index_topk_capacity(
    kernel: Kernel, tensors: Mapping[str, Tensor], span_max: int
) -> int:
    """``ROUTE.INDEX_TOPK``'s ``aux_id_0``: the compressed segment's width.

    A19's caution, restated by A20 for both operand rows and the one that
    bites: ``aux0`` is the segment, never the whole joined operand.  A backend
    that copies the output's last extent into it declares ``W + k`` where ``k``
    belongs, and the engine refuses -- ``ROUTE.INDEX_TOPK selects 2176
    positions and joins a 128-slot window into 2176 slots``.  The graph states
    the number (``top_k`` ranked, ``k`` dense), and the derivation A20 gives
    for a ``NO_ID`` ``aux0`` -- the output's slots minus the joined window's
    width -- is what stands in when it does not.

    ``compiler/backends/rom/common/program.py::_index_topk_capacity`` is the
    same rule.  It was not: this lane read ``top_k`` and that one read ``k``,
    which agreed on the ranked kernels because they declare both and disagreed
    on the dense ones, which declare only ``k`` -- so this lane fell back to
    the output's 2,176 columns, which is exactly the ``W + k`` the amendment
    says is refused.
    """
    slots = (
        matrix_shape(tensors[kernel.outputs[0]], span_max)[1]
        if kernel.outputs
        else 0
    )
    slot_map = _abi_input_slots(kernel, list(range(len(kernel.inputs))))
    window = 0
    if len(slot_map) > 1 and slot_map[1] is not None:
        window = matrix_shape(tensors[kernel.inputs[slot_map[1]]], span_max)[1]
    return index_topk_capacity(kernel, slots, window)


def index_topk_capacity(kernel: Kernel, slots: int, window: int) -> int:
    """``ROUTE.INDEX_TOPK``'s ``aux_id_0`` from the graph, or A20's derivation.

    ``slots`` is ``out0``'s last extent and ``window`` is ``in1``'s; the answer
    is the *compressed segment's* width, which is neither of them.  Both lanes
    call this arithmetic with the same two numbers, and a test compares them --
    they read two different attribute names before, ``top_k`` here and ``k``
    there, which agreed on every ranked kernel because those declare both and
    disagreed on every dense one because those declare only ``k``.
    ``compiler/backends/rom/common/program.py::index_topk_capacity`` is the
    twin.
    """
    declared = kernel.attributes.get("top_k", kernel.attributes.get("k"))
    if declared is not None:
        return int(declared)
    return int(slots) - int(window)


def _check_operand_arity(
    kernel: Kernel, engine: Any, bound: Sequence[int]
) -> str | None:
    """Does this kernel fill every mandatory ABI input slot?  Report if not.

    Nothing in this program compared the operands a kernel *has* against the
    operands its engine row *requires*, so a graph that named two of the three
    a subopcode reads produced an operator with ``NO_ID`` in a mandatory slot
    and the defect surfaced as a runtime trap in the simulator, one site at a
    time, hundreds of kernels after the compile that could have named all of
    them at once.

    The comparison is against the frozen table in ``compiler/ir/v3/lowering.py``
    -- the one table the exporters, the backends and the engines all read -- so
    it cannot drift from what an engine will actually ask for.  Slots the
    operand convention makes optional are named in ``_OPTIONAL_INPUTS`` and are
    always trailing; everything else must be present.  ``bound`` is what this
    backend will really put in the operator, after its own slot permutation and
    after any operand it synthesises, because an operand the backend supplies
    is not missing.

    Amendment A20: a slot the kernel declares in ``absent_operands`` is
    *accounted for* rather than missing.  It is the static counterpart of
    ``operand_present_predicate`` -- the graph states that the operator reads
    nothing there, the frozen ``OPTIONAL_INPUT_SLOTS`` has already agreed the
    row allows it, and the engine reads the slot through ``optional_input``.
    Counting it as a shortfall is what made the dense compressed index refuse
    at plan time with ``binds 2 input views where ROUTE.4 requires 3``, which
    was this check reading a stated hole as an unfilled mandatory slot.
    """
    limit = int(engine.inputs)
    optional = int(_OPTIONAL_INPUTS.get(kernel.kind, 0))
    required = limit - optional
    count = len(bound) + len(_declared_holes(kernel))
    if count > limit:
        return (
            f"{kernel.kernel_id} ({kernel.kind}): binds {count} input views "
            f"where {Major(engine.family).name}.{int(engine.sub)} takes {limit}"
        )
    if count < required:
        return (
            f"{kernel.kernel_id} ({kernel.kind}): binds {count} input views "
            f"where {Major(engine.family).name}.{int(engine.sub)} requires "
            f"{required}"
            + (f" (and admits {limit})" if limit != required else "")
        )
    if len(kernel.outputs) > int(engine.outputs):
        return (
            f"{kernel.kernel_id} ({kernel.kind}): declares "
            f"{len(kernel.outputs)} outputs where "
            f"{Major(engine.family).name}.{int(engine.sub)} writes "
            f"{int(engine.outputs)}"
        )
    return None


def _conforming_input_order(
    kernel: Kernel, engine: Any, tensors: Mapping[str, Tensor]
) -> tuple[list[int], list[int]]:
    """Return ``(ABI slot order, dropped IR slots)`` for one kernel's inputs.

    The neutral IR fixes *which* tensors an operation reads; TA-ABI3-OPCONV-1
    fixes *which slot* each one occupies.  Reconciling the two is the backend's
    job -- an engine rejects a non-conforming operator rather than guessing.
    """
    order = list(range(len(kernel.inputs)))
    permutation = _SLOT_PERMUTATION.get(kernel.kind)
    if permutation is not None and len(order) == len(permutation):
        order = [order[slot] for slot in permutation]
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
    undeclared_windows: list[str] | None = None,
) -> tuple[int, ...]:
    """Auxiliary IDs required by TA-ABI3-OPCONV-1 for this subopcode."""
    attributes = dict(kernel.attributes)
    family, sub = int(engine.family), int(engine.sub)
    aux: list[int] = []
    if undeclared_windows is None:
        undeclared_windows = []

    def out_cols(slot: int = 0) -> int:
        if slot >= len(kernel.outputs):
            return 0
        return matrix_shape(tensors[kernel.outputs[slot]], span_max)[1]

    def in_cols(slot: int) -> int:
        if slot >= len(kernel.inputs):
            return 0
        return matrix_shape(tensors[kernel.inputs[slot]], span_max)[1]

    if kernel.kind in _SUBCASE and family in (int(Major.VECTOR),):
        # TA-ABI3-OPCONV-1 section 3 gives ``COMPRESS`` and ``MHC`` more than a
        # sub-case: ``MHC`` names the Sinkhorn iteration count in ``aux1`` and
        # ``hc_mult`` in ``aux2``, and ``COMPRESS`` names the compression ratio
        # in ``aux1``.  Emitting only the sub-case left those slots ``NO_ID``,
        # and the engines refuse an operator that does not state them -- an
        # unstated stream count is a shape the engine cannot check the operands
        # against, which is exactly what the aux slots exist to prevent.
        aux = [_SUBCASE[kernel.kind]]
        if sub == int(Vector.SCALE):
            # ``VECTOR.SCALE`` has three sub-cases and the kind name settles
            # only two of them.  A kernel named ``SCALE`` that binds a second
            # operand is the elementwise product, not a constant scale: the
            # engine refuses sub-case 0 with ``input_view_1`` bound, and it is
            # right to -- the constant is in the numeric profile and the
            # operand would be ignored.  The operand map is the authority.
            if len(kernel.inputs) >= 2:
                aux = [1]
            elif kernel.kind != "SIGMOID":
                aux = [0]
        elif sub == int(Vector.MHC):
            aux.append(int(attributes.get("sinkhorn_iterations", NO_ID)))
            aux.append(int(attributes.get("hc_mult", NO_ID)))
        elif sub == int(Vector.COMPRESS):
            aux.append(int(attributes.get("ratio", NO_ID)))
    elif family == int(Major.ATTENTION):
        aux = [
            _group_size(kernel, tensors, attributes),
            int(attributes.get("mask_mode", 0 if attributes.get("causal", True) else 1)),
            int(Symbol.CONTEXT_LENGTH),
            int(Symbol.POSITION_START),
        ]
        if sub == int(Attention.SPARSE):
            # The neutral attribute is ``block_size``; reading ``block_width``
            # found nothing and declared a one-wide block, which the frozen
            # DeepSeek sparse contract refuses -- it is 64.
            aux[1] = int(
                attributes.get("block_size", attributes.get("block_width", 0))
                or 0
            )
            if aux[1] <= 0:
                raise PlanError(
                    f"kernel {kernel.kernel_id}: ATTENTION.SPARSE must declare "
                    "its block width; the engine checks it against the frozen "
                    "contract and cannot infer it from the operands"
                )
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
                _index_topk_capacity(kernel, tensors, span_max),
                int(attributes.get("mask_mode", 0)),
                int(Symbol.CONTEXT_LENGTH),
                int(Symbol.POSITION_START),
            ]
        elif sub == int(Route.WINDOW_INDEX):
            # The graph declares ``window_size``.  This read ``window``, which
            # no exporter emits, so the key never hit and the fallback -- the
            # output's own column count -- was the number every one of these
            # operators carried.  It happened to be right for the 43 genuine
            # sliding-window kernels, because a 128-row window is written into
            # a 128-column output; it was 2,048 for the compressed-group
            # enumeration, whose output is 2,048 wide and whose window is not
            # 2,048 anything.  Two lanes read two different wrong keys and both
            # got 128 by unrelated coincidences, which is why nothing noticed.
            #
            # The fallback stays rather than becoming a refusal: a graph that
            # declares no window is declaring an index family this operator
            # does not produce, and that is a fact about the family, recorded
            # once in the deployment notes, not a per-kernel verdict this
            # function should be issuing.
            window = attributes.get("window_size")
            if window is None:
                undeclared_windows.append(kernel.kernel_id)
                window = out_cols()
            aux = [
                int(window),
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
    elif family == int(Major.REDUCTION):
        if sub == int(Reduction.PARTITION_SUM):
            # TA-ABI3-OPCONV-1: this ``aux0`` is a runtime *symbol*, not an
            # immediate -- the opposite reading to GROUPED_CONCAT's below, and
            # the operand row is the authority for which.  No published graph
            # emits a PARTITION_SUM yet; the ROM lane has always stated it and
            # this lane stated nothing, which is a divergence waiting for the
            # first exporter to emit one rather than a defect anyone has hit.
            aux = [int(Symbol.VOCABULARY_PARTITIONS)]
        elif sub == int(Reduction.GROUPED_CONCAT):
            # Amendment A17: a concatenation states the axis it joins.  The
            # graph carries it as an attribute and ``aux_id_0`` is where the
            # ABI reads it; an unstated axis is read as 0, which is a *row*
            # join and silently the wrong operation for the two index joins
            # and the block-diagonal projection this model emits.  Emitting it
            # is the whole of what A17 asks a backend to do.
            aux = [int(attributes.get("axis", 0))]
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


def _lead_reduction_axis(kernel: Kernel, engine: Any) -> int:
    """The axis a reduction's contributions must be re-led by, or 0 for none.

    Every ``REDUCTION`` subopcode reduces ``input_view_0``'s **leading** axis
    and, for ``EXPERT_SUM``, takes exactly one weight per leading index.  A
    neutral reduction that names some other axis is not a different operation:
    it is the same arithmetic over a permuted *presentation* of the same
    elements, which is precisely what a strided view is for.  The mHC branch
    reduction is the case -- ``y[t,h] = sum_m pre[t,m] * x[t,m,h]`` names axis
    1, the four hyper-connection streams, because its operands are token-major
    -- and both the resolver and the verifier already anticipate it by name.

    Returning the axis here rather than in the emitter keeps one consequence
    visible where it is decided: a stream-major leading axis is not the token
    axis, so amendment A13's clamp no longer reaches the contributions view,
    and the token block must therefore be one row.
    """
    if int(engine.family) != int(Major.REDUCTION):
        return 0
    axis = int(kernel.attributes.get("reduction_axis", 0) or 0)
    if axis < 0:
        raise PlanError(
            f"kernel {kernel.kernel_id}: reduction_axis {axis} is negative"
        )
    return axis


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


def _pass_depth(
    kernel: Kernel, tensors: Mapping[str, Tensor], span_max: int, tile: TileConfig
) -> int:
    """The depth a non-contraction operation reduces or passes over.

    Attention reduces over the head dimension, so that is its depth.  A lookup,
    a movement or an elementwise pass reduces over nothing and makes one pass,
    which is a depth of one.  Zero would mean "unstated", and a cycle model
    cannot decompose an operation whose tile shape says nothing.
    """
    engine = engine_for(kernel.kind)
    if int(engine.family) == int(Major.ATTENTION) and kernel.inputs:
        shape = tensors[kernel.inputs[0]].shape
        if shape:
            head_dim, _ = _extent_value(shape[-1], span_max)
            return choose_tile(max(int(head_dim), 1), tile.depth)
    domain = _domain_extent(kernel, ("reduction_width", "reduction", "depth"), span_max)
    if domain:
        return choose_tile(domain, tile.depth)
    return 1


def _scale_row_block(tensors: Mapping[str, Tensor], tensor_id: str) -> int:
    """How many leading rows one of a weight's scale codes covers.

    The neutral IR names the block along the reduction axis; the scale tensor's
    own declared shape carries the block along the leading one, because a
    ``[1024, 4096]`` weight with a 128-element block whose scale is ``[8, 32]``
    is scaled in 128 x 128 tiles and ``1024 / 8`` says so.  A weight with no
    scale, or a one-dimensional MXFP4 scale, gives one, which every extent
    divides -- so this constrains nothing that amendment A8 already allowed.
    """
    tensor = tensors.get(tensor_id)
    if tensor is None or not tensor.scale_tensor_id:
        return 1
    scale = tensors.get(tensor.scale_tensor_id)
    block = int(tensor.scale_block_elements or 0)
    if scale is None or block <= 0:
        return 1

    def extent(value: Any) -> int:
        if isinstance(value, Symbolic):
            return max(int(value.maximum or 1), 1)
        return max(int(value), 1)

    rows = 1
    for value in tensor.shape[:-1]:
        rows *= extent(value)
    scale_rows = 1
    for value in scale.shape[:-1]:
        scale_rows *= extent(value)
    if scale_rows <= 0 or rows % scale_rows:
        return 1
    return max(rows // scale_rows, 1)


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
    stream_kernels: Mapping[int, tuple[str, int]],
    rolling_tensors: Mapping[str, tuple[str, int]],
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
    arity_faults: list[str] = []
    # ``ROUTE.WINDOW_INDEX`` operators whose kernel declared no ``window_size``.
    # Recorded rather than refused: a graph that declares no window is naming
    # an index family this operator does not produce, which is a fact about the
    # family and belongs in one line of the manifest, not in a per-kernel
    # verdict from the aux-id builder.
    undeclared_windows: list[str] = []
    placement_by_tensor = {p.tensor_id: p for p in placements}
    # Tensors written by a join whose extent the phase decides.  Every view of
    # such a tensor states that phase's own function -- the producer's and the
    # consumer's -- so the kernel that reads one needs the loop that resolves
    # the context form just as the producer does.  Left unresolved, this lane
    # read the *span's* group count for a context-sized operand and presented a
    # whole 128-group block where the request had eight.
    phase_extent_tensors = {
        name
        for kernel in graph.kernels
        if kernel.attributes.get("phase_symbol_binding")
        for name in kernel.outputs
    }
    # Expert ownership is a placement property, not a spelling convention.
    # A layer is expert-sharded only when its routed bank divides exactly over
    # the admitted nodes; smaller diagnostic MoEs keep the existing column
    # sharding and must not acquire a reduction that would sum replicas.
    expert_sharded_layers: set[int | None] = set()
    if node_count > 1:
        for routed in graph.kernels:
            if routed.kind != "ROUTED_MATMUL" or len(routed.inputs) < 2:
                continue
            bank_extent = expert_bank_extent(
                routed, tensors[routed.inputs[1]], span_max
            )
            if bank_extent >= node_count and bank_extent % node_count == 0:
                expert_sharded_layers.add(routed.layer)
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
        if not kernel.state_writes and kernel.kind != "CONCAT":
            # Two kernels are re-expressed by the emitter rather than emitted
            # as their table row: a state append becomes one write per source
            # into its own column range of the state row, and an axis-one
            # concatenation becomes one movement per column window.  Both bind
            # an operand row this planner's slot order does not describe, so
            # the row they would have had is not the row they get, and
            # checking it here would be checking the wrong thing.
            complaint = _check_operand_arity(kernel, engine, slot_order)
            if complaint is not None:
                arity_faults.append(complaint)
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

        # A reduction whose reduced axis is not the leading one is emitted one
        # token at a time.  ``REDUCTION.EXPERT_SUM`` reduces ``input_view_0``'s
        # leading axis, so the mHC branch reduction -- which reduces the four
        # hyper-connection streams while its operands put tokens first -- is
        # presented stream-major.  A stream-major view's leading axis is then
        # not the token axis, so amendment A13's clamp does not reach it (the
        # resolver derives that from the term stride and says so), and a block
        # larger than one token would present a whole block of tokens against
        # an output clamped to the rows the request actually has.  One token per
        # descriptor makes the two agree exactly, at every span, with no
        # partial final iteration to clamp.
        kernel_block = 1 if _lead_reduction_axis(kernel, engine) else block
        if int(engine.family) == int(Major.REDUCTION) and int(engine.sub) == int(
            Reduction.EXPERT_SUM
        ):
            # ``REDUCTION.EXPERT_SUM`` reduces its whole leading axis to one
            # row -- that is the operation, not a property of any operand -- so
            # a dispatch covers exactly one output row and the token block is
            # one.  A 512-token block presented six contributions per token
            # against a 512-row output and the engine said so plainly:
            # ``reduction output view holds 425,984 elements, expected 4,096``.
            kernel_block = 1
        if is_row_gather(kernel, tensors):
            # One token per dispatch: the row axis the engine indexes is then
            # the token's own trailing axis, and the index values are offsets
            # inside it rather than row numbers of a block.
            kernel_block = 1
        context_op = (int(engine.family), int(engine.sub)) in CONTEXT_LOOP_OPS
        phase_context = bool(kernel.attributes.get("phase_symbol_binding")) or any(
            name in phase_extent_tensors for name in kernel.inputs
        )
        if context_op:
            # A18 names one request-determined axis per view and this
            # operator's row has two.  The token axis is the one that becomes
            # static: a per-token dispatch makes it a literal one, with no
            # partial final iteration to clamp, leaving the candidate axis as
            # the only extent the request moves.  The cost is one dispatch per
            # token for this operator -- the trade the routed contraction and
            # the expert reduction already make -- and it is bounded by the
            # capability's own loop trip rather than by the context.
            kernel_block = 1
        stream_spec = stream_kernels.get(kernel.index)
        if stream_spec is not None:
            # Every member of a fixed-address pipeline shares one loop
            # divisor. In particular this makes INDEX_TOPK one-token like its
            # score producer, and lets EXPERT_SUM reduce six contribution
            # planes for a whole token block rather than materialising the
            # complete context.
            kernel_block = int(stream_spec[1])

        out_name = kernel.outputs[0] if kernel.outputs else None
        if out_name is not None:
            rows, cols, symbolic = matrix_shape(tensors[out_name], span_max)
        else:
            rows, cols, symbolic = 1, 1, False
        if not symbolic and int(engine.family) == int(Major.DMA) and int(
            engine.sub
        ) == int(Dma.SCATTER):
            # A scatter's output is the cache it *addresses*, whose extent is
            # fixed; what it iterates is the value operand, one row per token.
            # Taking the iteration from the destination gave the operation no
            # token-block loop at all, so its value view claimed every row the
            # declared context could ever hold and its index vector was the
            # whole position range rather than this request's rows.
            for name in kernel.inputs:
                value_rows, _, value_symbolic = matrix_shape(
                    tensors[name], span_max
                )
                if value_symbolic:
                    rows, symbolic = value_rows, True
                    break
        if symbolic:
            rows = round_up(rows, kernel_block)

        shard_columns = cols
        depth = 0
        groups = 1
        transposed = False
        bank = 0
        bank_shard = 0
        if contraction and len(kernel.inputs) >= 2:
            a_rows, a_cols, _ = matrix_shape(tensors[kernel.inputs[0]], span_max)
            w_rows, w_cols, _ = matrix_shape(tensors[kernel.inputs[1]], span_max)
            # A routed bank's leading axis is the expert, not an output row.
            # Folding it in made a 256-expert ``[256, 2048, 4096]`` operand
            # declare 524,288 output rows against a 2,048-column result, which
            # is the warning that said so.
            bank = expert_bank_extent(kernel, tensors[kernel.inputs[1]], span_max)
            if bank:
                w_rows //= bank
                if kernel.layer in expert_sharded_layers:
                    bank_shard = bank // node_count
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
            # A block-scaled weight may not be cut finer than its scale tile.
            # Amendment A15 states the scale index over whole tiles and refuses
            # a view whose leading extent is not a multiple of the row block,
            # because a partial tile has no code of its own; the released
            # DeepSeek FP8 projections tile 128 x 128, so a 512-column
            # projection over 32 nodes would ask for 16 rows of a 128-row tile.
            # Replication is the existing answer to a column count a node count
            # cannot cut, and it is the answer here too.
            row_block = _scale_row_block(tensors, kernel.inputs[1])
            if bank_shard:
                # Routed banks are partitioned on their expert axis.  Each
                # owner needs every output column of its local experts, and the
                # partial rows are joined by the explicit route-class-3 sum
                # before EXPERT_REDUCE consumes them.
                shard_columns = cols
            elif node_count > 1 and cols % node_count == 0 and cols > node_count:
                if (cols // node_count) % row_block:
                    warnings.append(
                        f"kernel {kernel.kernel_id}: {cols} output columns over "
                        f"{node_count} nodes is {cols // node_count} rows per "
                        f"node, which is not a whole number of the weight's "
                        f"{row_block}-row scale tiles; this contraction is "
                        "replicated instead of sharded"
                    )
                else:
                    shard_columns = cols // node_count
            elif node_count > 1:
                warnings.append(
                    f"kernel {kernel.kernel_id}: {cols} output columns are not "
                    f"divisible by {node_count} nodes; this contraction is "
                    "replicated instead of sharded"
                )

        # Tile shape for the SCHEDULE descriptor.  These are hardware tiles, not
        # program loops: the engine decomposes one operator this way and the
        # cycle model costs it from exactly these numbers, so every field has to
        # state something.  An operation with no contraction axis still has a
        # depth: a lookup or an elementwise pass makes one pass over its row,
        # and attention's depth is the head dimension it reduces over.
        tile_rows = choose_tile(max(rows, 1), tile.rows) if not symbolic else tile.rows
        tile_cols = choose_tile(max(shard_columns, 1), tile.cols)
        if depth:
            tile_depth = choose_tile(depth, tile.depth)
        else:
            tile_depth = _pass_depth(kernel, tensors, span_max, tile)

        row_loop = None
        if symbolic:
            row_loop = LoopPlan(
                loop_key=f"k{kernel.index}.block",
                kind="row",
                # Amendment A18: the loop counts blocks of the *bound symbol*,
                # not rows of whichever operand happened to be the principal.
                # Taking it from the output's maximum gave a group axis a
                # quarter of the iterations it needs, and gave the attention
                # join one more than it has -- the extra block being exactly
                # the 128-row window the join carries but the request does not
                # supply.
                trip=max(-(-span_max // kernel_block), 1),
                symbol="span_tokens",
                divisor=kernel_block,
            )

        context_loop = None
        if context_op or phase_context:
            # One block over the whole declared capacity: the loop runs once at
            # every request, and what it carries is A18's resolution of the
            # candidate axis.  The divisor is in the bound symbol's own units,
            # so it is the capacity times the compression ratio -- 65,536
            # groups of four is the whole 262,144-position context, and one
            # iteration covers all of it.
            axes = [
                context_axis_of(tensors[name], span_max)
                for name in (*kernel.inputs, *kernel.outputs)
            ]
            named = next((a for a in axes if a is not None), None)
            if named is None and context_op:
                raise PlanError(
                    f"kernel {kernel.kernel_id!r} lowers to an operator whose "
                    "row states a context-sized axis, but no operand declares "
                    "one; the loop that would resolve it has nothing to bind"
                )
            if named is None:
                # A consumer of a phase-split join: no operand *declares* a
                # context-sized axis, because the declared symbol is the
                # prefill one.  The decode path states the context form on the
                # view instead, and this is the loop that resolves it -- one
                # block over the whole context, run once, which is what
                # ``_open_context_loop`` gives a request-sized plane.
                divisor = max(int(span_max), 1)
            else:
                _axis, context_extent = named
                capacity = context_extent.numerator * span_max // context_extent.unit
                divisor = max(
                    capacity * context_extent.unit
                    // max(context_extent.numerator, 1),
                    1,
                )
            context_loop = LoopPlan(
                loop_key=f"k{kernel.index}.context",
                kind="context",
                trip=1,
                symbol="context_length",
                divisor=divisor,
            )

        operands: list[OperandPlan] = []
        for abi_slot, ir_slot in enumerate(_abi_input_slots(kernel, slot_order)):
            if ir_slot is None:
                continue  # a slot the convention requires to stay NO_ID
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
                    block=kernel_block,
                    transposed=transposed,
                    node_count=node_count,
                    shard_columns=shard_columns,
                    sharded=shard_columns != cols,
                    depth=depth,
                    bank=bank,
                    bank_shard=bank_shard,
                    context=context_loop is not None,
                    rolling=kernel.inputs[ir_slot] in rolling_tensors,
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
                    block=kernel_block,
                    transposed=transposed,
                    node_count=node_count,
                    shard_columns=shard_columns,
                    sharded=shard_columns != cols,
                    depth=depth,
                    bank=bank,
                    bank_shard=bank_shard,
                    context=context_loop is not None,
                    rolling=name in rolling_tensors,
                )
            )

        link_class = ""
        if node_count > 1:
            if (
                kernel.kind == "EXPERT_DISPATCH"
                and kernel.layer in expert_sharded_layers
            ):
                link_class = LINK_CLASS_BY_KIND[kernel.kind]
            elif (
                kernel.kind == "EXPERT_REDUCE"
                and kernel.layer in expert_sharded_layers
                and int(kernel.attributes.get("top_k", 0) or 0) > 0
            ):
                link_class = LINK_CLASS_BY_KIND[kernel.kind]
            elif kernel.kind == "ATTENTION_SPARSE":
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
                block_rows=kernel_block,
                tile_rows=tile_rows,
                tile_cols=tile_cols,
                tile_depth=tile_depth,
                row_loop=row_loop,
                context_loop=context_loop,
                operands=tuple(operands),
                aux=_aux_ids(
                    kernel,
                    engine,
                    tensors,
                    graph,
                    span_max,
                    groups,
                    undeclared_windows,
                ),
                slot_order=tuple(slot_order),
                groups=groups,
                phases=tuple(kernel.phases),
                link_class=link_class,
                shard_columns=shard_columns,
                depth=depth,
                stream_group=stream_spec[0] if stream_spec is not None else "",
            )
        )
    if arity_faults:
        shown = arity_faults[:12]
        more = len(arity_faults) - len(shown)
        raise PlanError(
            f"{len(arity_faults)} kernel(s) do not fill the operand row their "
            "engine declares in the frozen lowering table, so the emitted "
            "operator would name NO_ID in a mandatory slot and the engine "
            "would refuse it at issue time:\n  "
            + "\n  ".join(shown)
            + (f"\n  ... and {more} more" if more else "")
        )
    if undeclared_windows:
        warnings.append(
            "ROUTE.WINDOW_INDEX operators declaring no window_size: "
            + ", ".join(sorted(undeclared_windows))
        )
    return tuple(plans), warnings


def _assign_weight_residency(
    groups: Sequence[WeightGroup],
    placements: Sequence[WeightPlacement],
    kernels: Sequence[KernelPlan],
    node_count: int,
) -> tuple[tuple[WeightGroup, ...], tuple[WeightPlacement, ...]]:
    """Bind every authenticated weight range to replica or shard ownership.

    A logical weight object can span many layers and, for leftovers, several
    unrelated tensors.  Residency is therefore decided per tensor from the
    views that can address it, then summarized on the containing object.  A
    tensor is node-sharded only when *every* emitted use carries the ``node``
    selector; one replicated use conservatively makes the whole tensor
    replicated.  Layer-loop representatives propagate their decision through
    ``role_key`` to the other layers in the same role.  A block-scale role is
    implicit in its data operand and inherits exactly the data role's decision.
    """
    placement_by_tensor = {placement.tensor_id: placement for placement in placements}
    tensor_modes: dict[str, set[str]] = {}
    role_modes: dict[str, set[str]] = {}

    for kernel in kernels:
        for operand in kernel.operands:
            if operand.residence != "weight":
                continue
            mode = (
                "node_sharded"
                if node_count > 1 and "node" in operand.terms
                else "replicated"
            )
            tensor_modes.setdefault(operand.tensor_id, set()).add(mode)
            placement = placement_by_tensor[operand.tensor_id]
            if placement.role_key:
                role_modes.setdefault(placement.role_key, set()).add(mode)

    updated_placements: list[WeightPlacement] = []
    for placement in placements:
        modes = set(tensor_modes.get(placement.tensor_id, ()))
        if not modes and placement.role_key:
            modes.update(role_modes.get(placement.role_key, ()))
            if placement.role_key.endswith(".scale"):
                modes.update(role_modes.get(placement.role_key[:-6], ()))
        residency = (
            "node_sharded" if modes == {"node_sharded"} else "replicated"
        )
        updated_placements.append(
            replace(
                placement,
                residency=residency,
                shard_count=node_count if residency == "node_sharded" else 1,
            )
        )

    updated_by_tensor = {
        placement.tensor_id: placement for placement in updated_placements
    }
    updated_groups: list[WeightGroup] = []
    for group in groups:
        modes = {
            (
                updated_by_tensor[segment.tensor_id].residency
                if segment.tensor_id in updated_by_tensor
                else "replicated"
            )
            for segment in group.segments
        }
        residency = next(iter(modes)) if len(modes) == 1 else "mixed"
        updated_groups.append(replace(group, residency=residency))
    return tuple(updated_groups), tuple(updated_placements)


def _materialize_node_local_weights(
    graph: KernelGraph,
    groups: Sequence[WeightGroup],
    placements: Sequence[WeightPlacement],
    kernels: Sequence[KernelPlan],
    node_count: int,
) -> tuple[tuple[WeightGroup, ...], tuple[WeightPlacement, ...]]:
    """Turn logical shard ownership into authenticated node-local sources.

    The checkpoint lock authenticates complete binding segments, not arbitrary
    byte slices.  A tensor is therefore materialised as a physical per-node
    shard only when its ordered segment list divides into ``node_count`` equal
    byte runs *at segment boundaries*.  Dense one-segment tensors conservatively
    remain fully replicated; their existing ``NODE_ID`` tensor-view term still
    selects the node's logical column slice from that local replica.  A
    transposed dense contraction also remains replicated because its node
    selection is a strided column set rather than one contiguous source run.

    Weight and block-scale companion objects are an ABI-coupled pair: the
    scale address is derived from the weight view's element offset and has no
    independent offset field.  Likewise, a folded role needs one constant
    layer stride.  Eligibility is consequently all-or-nothing across every
    member of a role and across its data/scale pairs.
    """

    if node_count <= 1:
        return tuple(groups), tuple(placements)

    placement_by_tensor = {
        placement.tensor_id: placement for placement in placements
    }
    segments_by_tensor: dict[str, tuple[PlacedSegment, ...]] = {}
    for group in groups:
        ordered: dict[str, list[PlacedSegment]] = {}
        for segment in group.segments:
            ordered.setdefault(segment.tensor_id, []).append(segment)
        segments_by_tensor.update(
            (tensor_id, tuple(segments))
            for tensor_id, segments in ordered.items()
        )

    def partition(
        tensor_id: str,
    ) -> tuple[tuple[PlacedSegment, ...], ...] | None:
        """Equal consecutive runs whose boundaries are authenticated."""

        segments = segments_by_tensor.get(tensor_id, ())
        total = sum(int(segment.bytes) for segment in segments)
        if not segments or total <= 0 or total % node_count:
            return None
        per_node = total // node_count
        if per_node <= 0:
            return None
        out: list[tuple[PlacedSegment, ...]] = []
        current: list[PlacedSegment] = []
        current_bytes = 0
        for segment in segments:
            size = int(segment.bytes)
            if size <= 0 or current_bytes + size > per_node:
                return None
            current.append(segment)
            current_bytes += size
            if current_bytes == per_node:
                out.append(tuple(current))
                current = []
                current_bytes = 0
        if current or len(out) != node_count:
            return None
        placement = placement_by_tensor[tensor_id]
        if placement.elements % node_count:
            return None
        if bytes_for(placement.elements // node_count, placement.dtype) != per_node:
            return None
        return tuple(out)

    partitions: dict[str, tuple[tuple[PlacedSegment, ...], ...]] = {}
    contiguous_slice: dict[str, bool] = {}
    for kernel in kernels:
        for operand in kernel.operands:
            if operand.residence != "weight" or "node" not in operand.terms:
                continue
            # A normal [N,K] shard is one consecutive row-major byte run.  A
            # transposed [K,N] view selects strided columns and cannot become a
            # compact local object without a forbidden relayout.  Routed banks
            # split their outer expert dimension, which remains consecutive
            # regardless of the inner matrix's presentation.
            safe = not operand.transposed or operand.bank_shard > 0
            contiguous_slice[operand.tensor_id] = (
                contiguous_slice.get(operand.tensor_id, True) and safe
            )
    eligible: dict[str, bool] = {}
    for placement in placements:
        pieces = (
            partition(placement.tensor_id)
            if placement.residency == "node_sharded"
            and contiguous_slice.get(placement.tensor_id, True)
            else None
        )
        eligible[placement.tensor_id] = pieces is not None
        if pieces is not None:
            partitions[placement.tensor_id] = pieces

    role_members: dict[str, list[str]] = {}
    for placement in placements:
        if placement.role_key:
            role_members.setdefault(placement.role_key, []).append(
                placement.tensor_id
            )
    tensor_by_id = {tensor.tensor_id: tensor for tensor in graph.tensors}

    # Propagate one failed member through its folded role and its block-scale
    # pair.  The small fixed point makes the rule independent of traversal
    # order (data role -> one scale -> the whole scale role, and vice versa).
    changed = True
    while changed:
        changed = False
        for members in role_members.values():
            shared = all(eligible.get(tensor_id, False) for tensor_id in members)
            for tensor_id in members:
                if eligible.get(tensor_id, False) != shared:
                    eligible[tensor_id] = shared
                    changed = True
        for tensor_id, tensor in tensor_by_id.items():
            scale_id = tensor.scale_tensor_id
            if tensor_id not in eligible or not scale_id or scale_id not in eligible:
                continue
            shared = eligible[tensor_id] and eligible[scale_id]
            if eligible[tensor_id] != shared:
                eligible[tensor_id] = shared
                changed = True
            if eligible[scale_id] != shared:
                eligible[scale_id] = shared
                changed = True

    updated: dict[str, WeightPlacement] = {
        placement.tensor_id: replace(
            placement,
            materialization=(
                "node_sharded"
                if eligible.get(placement.tensor_id, False)
                else "replicated"
            ),
        )
        for placement in placements
    }
    updated_groups: list[WeightGroup] = []

    for group in groups:
        tensor_order = tuple(dict.fromkeys(s.tensor_id for s in group.segments))
        if not any(eligible.get(tensor_id, False) for tensor_id in tensor_order):
            updated_groups.append(replace(group, materialization="replicated"))
            continue

        node_maps: list[list[PlacedSegment]] = [
            [] for _ in range(node_count)
        ]
        cursor = 0
        physical_modes: set[str] = set()
        for tensor_id in tensor_order:
            placement = updated[tensor_id]
            sharded = eligible.get(tensor_id, False)
            physical_modes.add("node_sharded" if sharded else "replicated")
            maps = (
                partitions[tensor_id]
                if sharded
                else tuple(segments_by_tensor[tensor_id] for _ in range(node_count))
            )
            local_bytes = sum(int(segment.bytes) for segment in maps[0])
            for node_id, source_segments in enumerate(maps):
                node_cursor = cursor
                if sum(int(segment.bytes) for segment in source_segments) != local_bytes:
                    raise PlanError(
                        f"weight {tensor_id}: node-local authenticated segments "
                        "do not have one symmetric byte extent"
                    )
                for segment in source_segments:
                    node_maps[node_id].append(
                        replace(
                            segment,
                            element_offset=elements_in(node_cursor, segment.dtype),
                        )
                    )
                    node_cursor += int(segment.bytes)
            updated[tensor_id] = replace(
                placement,
                element_offset=elements_in(cursor, placement.dtype),
                elements=(
                    placement.elements // node_count
                    if sharded
                    else placement.elements
                ),
            )
            cursor += local_bytes

        # Re-derive the induction stride from the physical offsets.  This is
        # smaller by N for sharded expert roles and unchanged for replicated
        # fallbacks, including their block-scale companion roles.
        roles = {
            updated[tensor_id].role_key
            for tensor_id in tensor_order
            if updated[tensor_id].role_key
        }
        for role_key in roles:
            members = sorted(
                (
                    updated[tensor_id]
                    for tensor_id in tensor_order
                    if updated[tensor_id].role_key == role_key
                ),
                key=lambda item: int(item.layer or 0),
            )
            stride = 0
            if len(members) > 1:
                strides = {
                    right.element_offset - left.element_offset
                    for left, right in zip(members, members[1:])
                }
                if len(strides) != 1:
                    raise PlanError(
                        f"weight role {role_key}: node-local materialization "
                        "does not have one constant layer stride"
                    )
                stride = next(iter(strides))
            for member in members:
                updated[member.tensor_id] = replace(
                    updated[member.tensor_id], layer_stride_elements=stride
                )

        materialization = (
            next(iter(physical_modes)) if len(physical_modes) == 1 else "mixed"
        )
        updated_groups.append(
            replace(
                group,
                local_size_bytes=cursor,
                node_segments=tuple(tuple(segments) for segments in node_maps),
                materialization=materialization,
            )
        )

    return tuple(updated_groups), tuple(
        updated[placement.tensor_id] for placement in placements
    )


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
    bank: int = 0,
    bank_shard: int = 0,
    context: bool = False,
    rolling: bool = False,
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
    weight_bank = 0
    weight_bank_shard = 0
    # Amendment A18.  The question the token-block loop asks of an operand is
    # not "is your declared maximum the kernel's?" -- which compares two
    # numbers that a *join* is entitled to disagree on, and which left the
    # attention KV join with a clamped output and unclamped inputs -- but "is
    # your extent a function of the symbol this loop is bound to?".  The
    # coefficients answer it and travel to the view.
    extent = request_extent_of(tensor, span_max) if symbolic else None
    step = extent.step(block) if extent is not None else None
    if extent is None or step is None:
        extent, step = RequestExtent(), None
    # An axis the *context* sizes is one the token loop cannot resolve, so it
    # takes its own term and its own A18 declaration.  When the leading axis is
    # that axis there is no token term at all: the operand is not blocked by
    # the request's rows, it is sized by the context.
    context_named = context_axis_of(tensor, span_max) if context else None
    context_axis = context_named[0] if context_named is not None else -1
    context_extent = (
        context_named[1] if context_named is not None else RequestExtent()
    )
    if context_named is not None and context_axis == 0:
        extent, step = RequestExtent(), None
    if contraction and direction == "in" and slot == 1:
        # in1 is the weight, presented n-major as ``[N, K]`` -- or ``[E, N, K]``
        # when it is a routed bank, whose expert axis the engine addresses.
        weight_bank = bank
        weight_bank_shard = bank_shard
        view_rows = shard_columns
        view_cols = depth or cols
        if placement is not None and placement.layer_stride_elements:
            terms.append("layer")
        if sharded or bank_shard:
            terms.append("node")
    elif contraction and direction == "out" and slot == 0:
        view_cols = shard_columns
        if row_loop:
            view_rows = step if step is not None else block
            terms.append("row")
        if sharded:
            terms.append("node")
    else:
        if placement is not None and placement.layer_stride_elements:
            terms.append("layer")
        if row_loop and step is not None:
            # One iteration covers ``step`` elements of this axis and the
            # operand carries ``bias`` of them whatever the request is, so the
            # view claims exactly that many and never more -- which is the
            # bound A18 generalises from A13's ``dim0 <= bound_divisor``.  An
            # extent whose function this backend cannot write down keeps its
            # declared maximum, as every extent did before the amendment: the
            # loop's trip count is not its trip count and guessing one is the
            # silent wrong answer A18 exists to remove.
            view_rows = step + extent.bias
            terms.append("row")
    if context_named is not None:
        terms.append("context")
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
        bank=weight_bank,
        bank_shard=weight_bank_shard,
        # Declared only where a term resolves it: A18's third admission rule
        # refuses a view that names a function nothing can walk.
        extent_numerator=extent.numerator if "row" in terms else 1,
        extent_unit=extent.unit if "row" in terms else 1,
        extent_bias=extent.bias if "row" in terms else 0,
        context_axis=context_axis,
        context_numerator=context_extent.numerator,
        context_unit=context_extent.unit,
        context_bias=context_extent.bias,
        rolling=rolling,
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
        place(f"weight.{group.group_id}", group.materialized_size_bytes, 12)
    for constant in generated:
        place(f"generated.{constant.tensor_id}", constant.size_bytes, 12)
    for state in states:
        if is_direct_buffer_state(state.state_class):
            place(f"state.{state.physical_id}.direct", state.size_bytes, 12)
        else:
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
    placements: Sequence[WeightPlacement],
    generated: Sequence[GeneratedConstant],
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
    placement_by_tensor = {
        placement.tensor_id: placement for placement in placements
    }
    group_tensor_bytes: dict[str, dict[str, int]] = {}
    for group in groups:
        members = group_tensor_bytes.setdefault(group.group_id, {})
        for segment in group.segments:
            members[segment.tensor_id] = (
                members.get(segment.tensor_id, 0) + segment.bytes
            )

    replicated_weight_bytes = 0
    node_sharded_weight_bytes = 0
    materialized_node_sharded_weight_bytes = 0
    fallback_replicated_weight_bytes = 0
    for group in groups:
        for tensor_id, size in group_tensor_bytes[group.group_id].items():
            placement = placement_by_tensor.get(tensor_id)
            shard_count = (
                max(int(placement.shard_count), 1) if placement is not None else 1
            )
            if shard_count > 1:
                node_sharded_weight_bytes += size
            else:
                replicated_weight_bytes += size
            if placement is not None and placement.materialization == "node_sharded":
                materialized_node_sharded_weight_bytes += size
            elif shard_count > 1:
                fallback_replicated_weight_bytes += size
    weight_bytes_per_node = sum(group.materialized_size_bytes for group in groups)
    generated_constant_bytes = sum(constant.size_bytes for constant in generated)
    arena_bytes = sum(a.size_bytes for a in arenas)
    state_bytes = sum(
        s.size_bytes * (1 if is_direct_buffer_state(s.state_class) else 2)
        for s in states
    )
    host_bytes = sum(int(o["size_bytes"]) for o in host_objects.values())
    sram_bytes = sum(r.size_bytes for r in sram_regions)
    communication_scratch_bytes = _communication_scratch_bytes(kernels, node_count)
    hbm_available = int(capability.memory["hbm"]["bytes"])
    sram_available = int(capability.memory["sram"]["bytes"])
    cluster_control_bytes = 64 if node_count > 1 else 0

    # Capacity is a node-local physical packing, not the span of the logical
    # global object namespace.  Reserve each local payload at the same 4 KiB
    # granularity the lowering declares, including generated constants and the
    # two cluster-only objects allocated after the planned address map.
    resident = 0
    resident_payload = 0

    def reserve(size: int) -> None:
        nonlocal resident, resident_payload
        if size <= 0:
            return
        resident = round_up(resident, 4096) + size
        resident_payload += size

    for group in groups:
        reserve(group.materialized_size_bytes)
    for constant in generated:
        reserve(constant.size_bytes)
    for state in states:
        reserve(state.size_bytes)
        if not is_direct_buffer_state(state.state_class):
            reserve(state.size_bytes)
    for arena in arenas:
        reserve(arena.size_bytes)
    reserve(cluster_control_bytes)
    reserve(communication_scratch_bytes)
    hbm_alignment_bytes = resident - resident_payload

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
        "replicated_weight_bytes": replicated_weight_bytes,
        "node_sharded_weight_bytes": node_sharded_weight_bytes,
        "materialized_node_sharded_weight_bytes": (
            materialized_node_sharded_weight_bytes
        ),
        "fallback_replicated_weight_bytes": fallback_replicated_weight_bytes,
        "weight_bytes_per_node": weight_bytes_per_node,
        "weight_replication_overhead_per_node": (
            weight_bytes_per_node
            - (weight_bytes + max(node_count, 1) - 1) // max(node_count, 1)
        ),
        "weight_objects": len(groups),
        "weight_segments": sum(len(g.segments) for g in groups),
        "weight_segments_per_node": sum(
            len(group.node_segments[0])
            if group.node_segments
            else len(group.segments)
            for group in groups
        ),
        "generated_constant_bytes": generated_constant_bytes,
        "activation_arena_bytes": arena_bytes,
        "activation_arena_slots": len(arenas),
        "state_bytes": state_bytes,
        "communication_scratch_bytes": communication_scratch_bytes,
        "cluster_control_bytes": cluster_control_bytes,
        "hbm_alignment_bytes": hbm_alignment_bytes,
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


def _communication_scratch_bytes(
    kernels: Sequence[KernelPlan], node_count: int
) -> int:
    """Maximum symmetric participant array needed by one in-flight exchange.

    The lowering serially reuses one exported HBM object: every pack and unpack
    is assigned to the same dedicated DMA queue with ``max_outstanding=1``, and
    the deployment certificate reconstructs that schedule from the emitted
    descriptors.  Capacity therefore owes the largest array, not the sum of
    every communication site and not zero (the old proof counted lowerer-
    created exchange objects nowhere).
    Every extent here is a fixed token block; no maximum-context activation is
    reintroduced by the fabric schedule.
    """

    if node_count <= 1:
        return 0
    largest = 0
    for kernel in kernels:
        operand: OperandPlan | None = None
        if kernel.link_class in {"activation_transfer", "expert_dispatch"}:
            operand = next(
                (
                    item
                    for item in kernel.operands
                    if item.direction == "out" and item.slot == 0
                ),
                None,
            )
        elif kernel.link_class == "reduction":
            operand = next(
                (
                    item
                    for item in kernel.operands
                    if item.direction == "in" and item.slot == 0
                ),
                None,
            )
        elif kernel.link_class == "sparse_gather":
            operand = next(
                (
                    item
                    for item in kernel.operands
                    if item.direction == "in" and item.slot == 1
                ),
                None,
            )
        if operand is None:
            continue
        columns = (
            kernel.shard_columns
            if kernel.link_class == "activation_transfer"
            else operand.tile_cols
        )
        participants = node_count
        if kernel.link_class == "sparse_gather":
            # Each node contributes one disjoint 1/N feature band.  The N
            # participant slots therefore hold exactly one reconstructed KV
            # block in total, which ALL_GATHER leaves on every node.
            columns //= node_count
        largest = max(
            largest,
            bytes_for(
                participants * max(operand.tile_rows, 1) * max(columns, 1),
                operand.dtype,
            ),
        )
    return round_up(largest, 4096)
