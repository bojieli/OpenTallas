"""AM-E9: the one SCHEDULE emission rule, shared by every backend.

``docs/CHIP_ARCHITECTURE_DESIGN.md`` section 3.8 (AM-E9, registry entry in
section 10.1) states the rule the two lowerings of one graph must share:

    tile_rows = rows, tile_cols = 64, tile_depth = 128,
    issue_window = max_outstanding = 16

and section 7.2 records why: the shipped comparison lowered the same graph
through two private tile policies and handed the ROM side a 2x tensor-lane and
16x column-group advantage (``docs/PERFORMANCE_DESIGN_POSTMORTEM.md`` section
5; the C2 audit of ``results/derived/qwen3_n5_design_target_deployment_audit
.json`` lists 31 cost-bearing SCHEDULE asymmetries).  Every SCHEDULE field the
cycle model tiles by -- ``tile_rows``, ``tile_cols``, ``tile_depth``,
``issue_window``, ``max_outstanding``, ``queue_index``, ``port_mask`` and ``bank_mask``
-- is therefore ONE function of (operator shape, engine family, capability),
defined here and called by ``compiler/backends/rom/common/program.py`` and
``compiler/backends/hbm_sram/plan.py`` + ``lower.py``.  Neither backend may
carry a tile policy, or a scratchpad placement, of its own.

The rule, field by field
------------------------

``rows``
    The token rows ONE dispatch covers: ``1`` for a per-token dispatch, else
    the token block (512, ``compiler.qwen3.constants.TOKEN_BLOCK_ROWS`` /
    ``TileConfig.block``) for a symbolic-leading output, else the product of
    the output's static leading extents.  Never the span maximum: a SCHEDULE
    that priced a 512-row block as 8,192 rows would be wrong on both sides.
    Each backend states its own loop structure, so ``rows`` is an input of the
    rule; :func:`dispatch_rows` is the shared derivation for the common case.

``tile_rows = rows``
    Section 3.8 verbatim: the tile spans every row of the dispatch.  Row
    tiling is not a program construct on either side.

``tile_cols = choose_tile(cols, 64)``
    [T2.1-3]: a pass is 64 columns.  ``choose_tile`` (the HBM planner's
    largest-divisor rule, now shared) keeps every tile full, so a width that
    64 does not divide takes its largest divisor at or below 64.  ``cols`` is
    the operator's output width: the weight's N for a tensor contraction, the
    head dimension for attention, the output's last declared extent
    otherwise.  A capability that advertises fewer than 64 *column* lanes for
    a column-lane family (tensor, vector, attention, reduction) bounds the
    tile at its lane count; the ``lanes`` a capability publishes for the DMA,
    selection, state and link engines are movers and units ([T2.1-12]: four
    256 B/cycle movers; section 3.8: ``dma (8 lanes, 1,024 B/cycle)``) and the
    route engine's are key lanes (section 3.8: ``route (1,024 key lanes)``),
    not a column bound, and never narrow a tile.  On the Qwen pair every
    column-lane count is at least 64 on both vehicles, so the tile is 64 wide
    for every family on both sides.

``tile_depth = min(reduction, 128)`` for a contracting operator, ``1``
    otherwise.  [T2.1-3]: 128 K per pass; AM-E2 v2: 128 context positions per
    attention block.  ``reduction`` is the weight's K for MATMUL / GROUPED /
    ROUTED, the context-position extent for ATTENTION, the declared reduction
    extent of a REDUCTION operator, and 1 for every pass-shaped family
    (``runtime.cycle.model.REDUCING_FAMILIES`` reads depth for exactly the
    tensor, attention and reduction families).  The depth is a fixed block,
    not a divisor: a K or a context bound that 128 does not divide (Qwen's
    8,256-position bound) ends in a partial tail tile, which the cycle model
    charges as such (``_compute_cycles`` ``tail_depth``), and no view is ever
    built from ``tile_depth``.  The ROM macro row (2,048 BF16 elements) and
    the attention kernel's ``block_width`` attribute no longer reach the
    descriptor.

``tiles = ceil(rows / tile_rows) * ceil(cols / tile_cols) * ceil(reduction /
    tile_depth)`` -- the ROM backend's ``_tile_count`` formula, now shared.

``max_outstanding = min(16, tiles, limits.max_outstanding_per_queue)``
    [T2.1-15]: 16 outstanding per queue is the unified record's value; an
    operator with fewer tiles than that carries its tile count (the ROM
    checker's ``outstanding_has_work``).  Both vehicles publish a limit of at
    least 16 (rom_qwen3 16, hbm_sram_single_chip 64), so the value is the same
    on both sides.

``issue_window = max_outstanding``
    Section 3.8 verbatim.  The HBM backend's previous ``issue_window = queue
    count`` (4 / 2 / 2 / 4 / 1) and the ROM backend's ``min(tiles, 16)`` were
    the two origins of the 4x column-group asymmetry.

``queue_index = ordinal % Q``
    ``Q = min(published queues - reserved, E9_QUEUES[family])``.  ``E9_QUEUES``
    is the element-wise minimum of the pair's vehicle capabilities
    (rom_qwen3.json tensor 2 / vector 2 / dma 2 / attention 1 / reduction 1 /
    selection 1 / state 1; hbm_sram_single_chip.json 4 / 2 / 4 / 2 / 2 / 1 /
    1 / link 4): the design's [T2.1-14] tensor 4 / dma 4 / attention 2 cannot
    be served by rom_qwen3.json, so 2 / 2 / 2 / 1 is the one value for BOTH
    sides, and independent operators (section 10.3 item 4: q/k/v, gate/up)
    spread over the queues both vehicles have.  ``ordinal`` is the rank of the
    operator's source kernel among the graph's kernels that lower to the same
    engine family, in neutral-graph order (:func:`family_ordinals`) -- a fact
    about the graph, never about either backend's emission order.  An
    auxiliary operator a backend emits for a kernel in another family (the
    compressor's DMA primitives) takes the kernel's graph index.  ``reserved``
    is the number of trailing queues the backend keeps for something else --
    the HBM cluster's exchange queue (``_scratch_schedule_for``), which stays
    the last DMA queue and is never an ordinary operator's.

``port_mask = (1 << sram_ports) - 1``
    AM-C4: bit p = scratchpad port p.  ``sram_ports`` is ``memory.sram.ports``
    when the capability publishes it, else 2 ([T2.1-20]: two ports per bank);
    rom_qwen3.json publishes none and hbm_sram_single_chip.json publishes 2,
    so the value is 3 on both sides.  The ROM backend's previous port_mask --
    the SRAM *bank* index of each activation buffer -- was a bank set, and the
    cycle model reads the field as ports (``MemorySystem._allowed``: bits over
    ``ports_per_unit``).

``bank_mask = OR of 1 << STAGING_BANK[r] over ENGINE_STAGING_REGIONS[family]``
    AM-E9 v2 -- one activation-buffer placement, and the reason this field is
    now unified.  Bit b = scratchpad bank b of the staging regions the
    operator's engine family streams through, over ONE declared placement
    (:data:`STAGING_REGIONS`, :data:`ENGINE_STAGING_REGIONS`) that both
    backends call and that the HBM planner allocates against
    (``hbm_sram/plan.py _allocate_sram``).  ``rom_qwen3.json`` and
    ``hbm_sram_single_chip.json`` declare the SAME scratchpad -- 32 banks,
    134,217,728 B, 4 MiB per bank, two ports -- so one placement is
    expressible on both ([T2.1-20]; design section 7.2: staging, scratchpad
    ports, queues and mesh are the same for both twins).

    Bit b is bank b, not bank *group* b.  [T2.1-20] describes the scratchpad
    both ways -- "32 banks x 4 MiB" and "bank groups 0-15 ... (2 banks
    each)" -- and AM-C4's text says group.  The value is charged as a bank:
    ``MemorySystem._allowed`` iterates ``range(klass.units)``, and
    ``klass.units`` is ``memory.sram.banks`` (32).  The rule takes the reading
    that is charged, exactly as AM-E9 v1 did for ``port_mask``.  The declared
    regions occupy banks 0-7, inside the program-visible scratchpad either way
    ([T2.1-20] reserves banks 30-31 for the HOST region).

    The previous reading (AM-C4: bit b = bank group b of the STREAMED
    operand's store, ROM shards on one side and staging groups on the other)
    is withdrawn because nothing implements the typing it assumes.
    ``runtime.cycle.model.MemorySystem.schedule`` applies the field to the
    ``sram`` class and to nothing else -- ROM-, HBM- and HOST-class accesses
    are scheduled with mask 0 -- so the ROM backend's mask-ROM shard set was
    charged as a scratchpad-bank set, and the three families that read no
    weight at all (attention, dma, selection) were emitted ``0``, which
    ``MemorySystem._allowed`` reads as UNRESTRICTED: 64 of 64 scratchpad units
    against the HBM side's 2 to 4.  Design section 7.1 row 4 says of the ROM
    chip's freer staging pool "no overlap credited"; the previous emission
    credited exactly that overlap.  This is the same defect AM-E9 already
    fixed one field over (see ``port_mask`` above): a bank set in a field the
    model reads as something else.

    Measured on the Qwen decode (batch 1, context 8,192, one transaction) with
    only this field varied and no other change to program, machine or request
    -- a scratch harness that wraps the cycle model's own ``tile_mapping`` and
    replaces one field of the mapping it returns, re-timing one cached
    functional trace under each variant; the numbers are quoted in the commit
    that introduced this rule -- the direction and the magnitude are: at the N5 design-target machine the audit charges with, the
    swap is worth exactly 0 cycles on both sides (ROM 438,749 total cycles
    under every variant; HBM 22,752,774 under every variant, and provably
    insensitive because that decode issues 0 SRAM-class transactions); at
    asap7_v2, where the ROM decode makes 3,897,922 SRAM transactions, the ROM
    side spans 148,804,260 (every mask zero) .. 149,990,884 (as previously
    emitted) .. 151,322,992 (on the HBM staging placement) cycles, so the
    pair's headline ratio moved 1.68% on the choice of emission rule alone.
    The three weight-free families move 0 cycles in both directions on both
    machines: the argument against their old emission is structural (same
    class, same declared geometry, "no overlap credited"), not a cycle count.

    The ROM bank identity is not lost, and does not belong in this field:
    AM-C4's own last clause already keeps per-tile placement in the ROM plan
    (``route_table_digest``), ``noc_route_class`` still reconstructs from the
    same shards, and ``compiler/backends/rom/common/check.py`` now checks the
    shard reconstruction against the plan objects (``rom_shard_banks``, bounded
    by ``memory.rom.banks``) instead of against this descriptor, while
    ``bank_mask_capacity`` bounds the descriptor by ``memory.sram.banks`` --
    the store the field is actually charged to.  Likewise ``noc_route_class``
    (0 on a single chip on both sides) and the inert ``resource_bound`` /
    ``priority`` are left to each side.

No ABI change (section 10.3): every value stays inside the frozen SCHEDULE
fields and inside both capabilities' published limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from compiler.ir.v3.kernel_ir import Kernel, KernelGraph, Symbolic, Tensor
from compiler.ir.v3.lowering import engine_for
from runtime.abi3.constants import Major
from runtime.abi3.constants import Tensor as TensorOp

#: [T2.1-3]: a pass is 64 columns wide.
E9_TILE_COLS = 64
#: [T2.1-3]: a pass reduces 128 K; AM-E2 v2: 128 context positions per block.
E9_TILE_DEPTH = 128
#: [T2.1-15]: outstanding tiles per queue on the unified record.
E9_OUTSTANDING = 16
#: [T2.1-20]: two scratchpad ports per bank, used when a capability publishes
#: no ``memory.sram.ports``.
E9_SRAM_PORTS_DEFAULT = 2
#: [T2.1-20]: 32 scratchpad banks, used when a capability publishes no
#: ``memory.sram.banks``.  Both vehicles publish 32.
E9_SRAM_BANKS_DEFAULT = 32

#: AM-E9 v2: THE activation-buffer placement, in bank order.  One staging
#: region per scratchpad bank, bank index = position in this tuple, over the
#: 32-bank / 4 MiB-per-bank scratchpad both vehicles declare ([T2.1-20],
#: design section 7.2).  ``compiler/backends/hbm_sram/plan.py _allocate_sram``
#: allocates exactly these regions at exactly these banks (offset = bank x
#: bank_bytes), and both backends derive ``bank_mask`` from the same table, so
#: the same operator on the same graph names the same banks on both sides.
#: The single-node profiles allocate no ``sram.link_stage``; its bank is
#: reserved so that a cluster profile does not renumber the others.
STAGING_REGIONS: tuple[str, ...] = (
    "sram.activation_stage",
    "sram.weight_stage",
    "sram.accumulator",
    "sram.vector_stream",
    "sram.attention_working",
    "sram.route_index",
    "sram.state_stage",
    "sram.link_stage",
)

#: Staging region -> its scratchpad bank index.
STAGING_BANK: Mapping[str, int] = {
    region: index for index, region in enumerate(STAGING_REGIONS)
}

#: Staging regions each engine family streams through; the union is the
#: family's ``bank_mask``.  This was ``hbm_sram/lower.py _ENGINE_REGIONS``,
#: which only the HBM backend called; it is the shared table now.
ENGINE_STAGING_REGIONS: Mapping[int, tuple[str, ...]] = {
    int(Major.TENSOR): (
        "sram.activation_stage",
        "sram.weight_stage",
        "sram.accumulator",
    ),
    int(Major.DMA): ("sram.activation_stage", "sram.weight_stage"),
    int(Major.VECTOR): ("sram.vector_stream",),
    int(Major.REDUCTION): ("sram.vector_stream", "sram.accumulator"),
    int(Major.ATTENTION): ("sram.attention_working",),
    int(Major.ROUTE): ("sram.route_index",),
    int(Major.SELECTION): ("sram.vector_stream",),
    int(Major.STATE): ("sram.state_stage",),
    int(Major.LINK): ("sram.link_stage",),
}

#: Queues the rule spreads a family's operators over: the element-wise minimum
#: of the pair's vehicle capabilities (see the module docstring).  A family
#: absent here spreads over one queue.
E9_QUEUES: Mapping[int, int] = {
    int(Major.TENSOR): 2,
    int(Major.VECTOR): 2,
    int(Major.DMA): 2,
    int(Major.ATTENTION): 1,
    int(Major.REDUCTION): 1,
    int(Major.ROUTE): 1,
    int(Major.SELECTION): 1,
    int(Major.STATE): 1,
    int(Major.LINK): 1,
}

#: Families whose advertised ``lanes`` are column lanes and therefore bound
#: ``tile_cols``.  The DMA, selection, state and link engines publish movers
#: and units under the same key ([T2.1-12], section 3.8), and the route
#: engine publishes key lanes (section 3.8: ``route (1,024 key lanes)``);
#: none of those is a column bound.
COLUMN_LANE_FAMILIES = frozenset({
    int(Major.TENSOR),
    int(Major.VECTOR),
    int(Major.ATTENTION),
    int(Major.REDUCTION),
})

#: Capability ``engines`` key per family.
ENGINE_KEY_BY_FAMILY: Mapping[int, str] = {
    int(Major.DMA): "dma",
    int(Major.TENSOR): "tensor",
    int(Major.VECTOR): "vector",
    int(Major.ATTENTION): "attention",
    int(Major.ROUTE): "route",
    int(Major.REDUCTION): "reduction",
    int(Major.SELECTION): "selection",
    int(Major.STATE): "state",
    int(Major.LINK): "link",
}

#: Tensor sub-opcodes that contract a K axis (``TA-ABI3-OPCONV-1`` section 2).
TENSOR_CONTRACTIONS = frozenset({
    int(TensorOp.MATMUL),
    int(TensorOp.GROUPED_MATMUL),
    int(TensorOp.ROUTED_MATMUL),
})

WEIGHT_ROLES = frozenset({"weight", "constant"})

#: Iteration-domain keys the two exporters use for the contracted extent and
#: for the context-position extent.
REDUCTION_DOMAIN_KEYS: tuple[str, ...] = ("reduction_width", "reduction", "depth")
CONTEXT_DOMAIN_KEYS: tuple[str, ...] = ("context_tokens", "context_length")


@dataclass(frozen=True, slots=True)
class OperatorShape:
    """The three extents the rule tiles by, plus whether a K axis exists."""

    #: Token rows one dispatch covers (see the module docstring).
    rows: int
    #: Output width: weight N for a contraction, head_dim for attention, the
    #: output's last declared extent otherwise.
    cols: int
    #: Contracted extent: weight K, the context-position extent for attention,
    #: the declared reduction extent for REDUCTION, 1 otherwise.
    reduction: int
    #: True for the families whose depth the cycle model reads.
    contracts: bool


@dataclass(frozen=True, slots=True)
class E9Schedule:
    """Every SCHEDULE field the rule fixes, ready for ``builder.schedule``."""

    tile_rows: int
    tile_cols: int
    tile_depth: int
    tiles: int
    issue_window: int
    max_outstanding: int
    queue_index: int
    port_mask: int
    bank_mask: int


def choose_tile(extent: int, target: int) -> int:
    """Largest divisor of ``extent`` not exceeding ``target``.

    Divisor tiling removes edge tiles entirely: every tile of every loop is
    full, so one tensor view with one dynamic term covers the whole axis and
    the verifier's view-bound proof is exact rather than conservative.
    """
    if extent <= 0:
        raise ValueError(f"cannot tile a non-positive extent {extent}")
    limit = max(min(target, extent), 1)
    for candidate in range(limit, 0, -1):
        if extent % candidate == 0:
            return candidate
    return 1


def resolve_extent(value: Any, capability: Any) -> int:
    """A possibly symbolic extent at the largest value it can take.

    ``Symbolic.maximum`` already includes the multiplier; a symbol with no
    declared maximum takes the capability's context bound times its
    multiplier, exactly as both backends resolve it.
    """
    if isinstance(value, Symbolic):
        if value.maximum:
            return max(int(value.maximum), 1)
        bound = int(capability.limits["max_context_positions"])
        return max(bound * int(value.multiplier or 1), 1)
    return max(int(value), 1)


def dispatch_rows(tensor: Tensor | None, *, block: int, capability: Any) -> int:
    """Rows one dispatch of an operator writing ``tensor`` covers.

    A symbolic-leading output is walked in token blocks, so a dispatch covers
    one block; a static output is covered whole, its leading extents folded
    into rows the way the cycle model's ``operand_extents`` folds them.
    """
    if tensor is None or not tensor.shape:
        return 1
    if isinstance(tensor.shape[0], Symbolic):
        return max(int(block), 1)
    rows = 1
    for axis in tensor.shape[:-1]:
        rows *= resolve_extent(axis, capability)
    return max(rows, 1)


def _domain_extent(kernel: Kernel, keys: Sequence[str], capability: Any) -> int:
    for key in keys:
        value = kernel.iteration_domain.get(key)
        if value is None:
            continue
        extent = resolve_extent(value, capability)
        if extent > 0:
            return extent
    return 0


def operator_shape(
    kernel: Kernel,
    tensors: Mapping[str, Tensor],
    family: int,
    sub: int,
    *,
    rows: int,
    capability: Any,
) -> OperatorShape:
    """The rule's shape of one operator, read off the neutral kernel.

    ``rows`` is the backend's dispatch rows (:func:`dispatch_rows` in the
    common case); ``cols`` and ``reduction`` come from the graph alone so the
    two lowerings of one kernel cannot disagree about them.
    """
    family = int(family)
    inputs = [tensors[n] for n in kernel.inputs if n in tensors]
    outputs = [tensors[n] for n in kernel.outputs if n in tensors]
    weights = [t for t in inputs if t.role in WEIGHT_ROLES]
    output_width = (
        resolve_extent(outputs[0].shape[-1], capability)
        if outputs and outputs[0].shape
        else 1
    )
    cols = output_width
    reduction = 1
    contracts = False
    if family == int(Major.TENSOR) and int(sub) in TENSOR_CONTRACTIONS:
        weight_dims = (
            tuple(resolve_extent(d, capability) for d in weights[0].shape)
            if weights and weights[0].shape
            else ()
        )
        cols = (
            _domain_extent(kernel, ("output_width",), capability)
            or (weight_dims[0] if weight_dims else output_width)
        )
        reduction = (
            _domain_extent(kernel, REDUCTION_DOMAIN_KEYS, capability)
            or (weight_dims[-1] if weight_dims else 1)
        )
        contracts = True
    elif family == int(Major.ATTENTION):
        cols = _domain_extent(kernel, ("head_dim",), capability) or output_width
        reduction = _domain_extent(kernel, CONTEXT_DOMAIN_KEYS, capability)
        if reduction <= 0:
            reduction = int(capability.limits["max_context_positions"])
        contracts = True
    elif family == int(Major.REDUCTION):
        reduction = _domain_extent(kernel, REDUCTION_DOMAIN_KEYS, capability) or 1
        contracts = reduction > 1
    return OperatorShape(
        rows=max(int(rows), 1),
        cols=max(int(cols), 1),
        reduction=max(int(reduction), 1),
        contracts=contracts,
    )


def sram_ports(capability: Any) -> int:
    """``memory.sram.ports`` when published, else [T2.1-20]'s two."""
    sram = dict(capability.memory.get("sram", {}) or {})
    ports = int(sram.get("ports", 0) or 0)
    return ports if ports > 0 else E9_SRAM_PORTS_DEFAULT


def sram_banks(capability: Any) -> int:
    """``memory.sram.banks`` when published, else [T2.1-20]'s thirty-two."""
    sram = dict(capability.memory.get("sram", {}) or {})
    banks = int(sram.get("banks", 0) or 0)
    return banks if banks > 0 else E9_SRAM_BANKS_DEFAULT


def staging_bank_mask(family: int, capability: Any) -> int:
    """The scratchpad banks ``family`` streams through (AM-E9 v2).

    One value for both backends: the union of :data:`STAGING_BANK` over the
    family's :data:`ENGINE_STAGING_REGIONS`.  A capability whose scratchpad is
    too narrow to hold the declared placement is refused rather than folded
    modulo its bank count -- a placement that does not fit is a design point
    the shared rule does not describe, not a mask to invent.
    """
    banks = sram_banks(capability)
    mask = 0
    for region in ENGINE_STAGING_REGIONS.get(int(family), ()):
        bank = STAGING_BANK[region]
        if bank >= banks:
            raise ValueError(
                f"staging region {region} is bank {bank}, but the capability "
                f"publishes only {banks} scratchpad banks"
            )
        mask |= 1 << bank
    return mask


def column_lane_bound(family: int, capability: Any) -> int:
    """The widest tile the family's column lanes serve; 64 for mover engines."""
    family = int(family)
    if family not in COLUMN_LANE_FAMILIES:
        return E9_TILE_COLS
    spec = capability.engines.get(ENGINE_KEY_BY_FAMILY.get(family, ""), {}) or {}
    lanes = int(spec.get("lanes", 0) or 0)
    return lanes if lanes > 0 else E9_TILE_COLS


def queue_count(family: int, capability: Any, *, reserved: int = 0) -> int:
    """Queues the rule spreads ``family`` over on ``capability``."""
    family = int(family)
    spec = capability.engines.get(ENGINE_KEY_BY_FAMILY.get(family, ""), {}) or {}
    published = max(int(spec.get("queues", 1) or 1), 1)
    wanted = int(E9_QUEUES.get(family, 1))
    return max(min(published - max(int(reserved), 0), wanted), 1)


def family_ordinals(graph: KernelGraph) -> dict[int, tuple[int, int]]:
    """``kernel.index -> (lowered family, rank among that family)``.

    Graph order, graph families: the same on every backend that lowers the
    graph, whatever order each emits its instructions in.
    """
    ranks: dict[int, int] = {}
    out: dict[int, tuple[int, int]] = {}
    for kernel in graph.kernels:
        try:
            family = int(engine_for(kernel.kind).family)
        except KeyError:
            continue
        rank = ranks.get(family, 0)
        ranks[family] = rank + 1
        out[int(kernel.index)] = (family, rank)
    return out


def queue_ordinal(
    ordinals: Mapping[int, tuple[int, int]], kernel_index: int, family: int
) -> int:
    """The ordinal an operator of ``family`` emitted for ``kernel_index`` takes."""
    entry = ordinals.get(int(kernel_index))
    if entry is not None and entry[0] == int(family):
        return int(entry[1])
    return int(kernel_index)


def e9_schedule(
    shape: OperatorShape,
    family: int,
    capability: Any,
    *,
    ordinal: int,
    reserved_queues: int = 0,
) -> E9Schedule:
    """AM-E9 for one operator: the module docstring, as code."""
    family = int(family)
    tile_rows = max(int(shape.rows), 1)
    tile_cols = choose_tile(
        max(int(shape.cols), 1),
        min(E9_TILE_COLS, column_lane_bound(family, capability)),
    )
    tile_depth = min(max(int(shape.reduction), 1), E9_TILE_DEPTH) if shape.contracts else 1
    tiles = (
        -(-max(shape.rows, 1) // tile_rows)
        * -(-max(shape.cols, 1) // tile_cols)
        * -(-max(shape.reduction, 1) // tile_depth)
    )
    limit = int(capability.limits["max_outstanding_per_queue"])
    max_outstanding = max(min(E9_OUTSTANDING, tiles, limit), 1)
    issue_window = max_outstanding
    queues = queue_count(family, capability, reserved=reserved_queues)
    queue_index = int(ordinal) % queues
    port_mask = (1 << sram_ports(capability)) - 1
    bank_mask = staging_bank_mask(family, capability)
    return E9Schedule(
        tile_rows=tile_rows,
        tile_cols=tile_cols,
        tile_depth=tile_depth,
        tiles=tiles,
        issue_window=issue_window,
        max_outstanding=max_outstanding,
        queue_index=queue_index,
        port_mask=port_mask,
        bank_mask=bank_mask,
    )
