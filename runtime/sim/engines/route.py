"""ROUTE engine family: expert routing, sparse index selection and windowing.

Routing is where a MoE model decides *what work exists*, so every decision here
is made from device memory and is deterministic down to the tie break.  Two
rules hold across all ten subopcodes:

* a rank order is by descending key, and equal keys resolve to the lower index,
  so a re-run of the same scores selects the same experts in the same slots;
* an ID that names something outside its declared bound is a fault (trap class
  3) after being counted in ``route.rejected_ids``, never a clamp or a wrap.

``ROUTE.TOPK``
    ``input_view_0`` scores ``[groups, experts]`` (or ``[experts]``).
    ``output_view_0`` U32 selected expert IDs ``[groups, k]``,
    ``output_view_1`` optional selected weights ``[groups, k]``.
    ``aux_id_0`` is an immediate ``k``; ``NO_ID`` takes ``k`` from the output.

``ROUTE.BIASED_TOPK``
    DeepSeek routing.  ``input_view_1`` is the per-expert selection bias,
    ``[experts]`` or ``[groups, experts]``.  Selection ranks ``score + bias``;
    the weights written out are the *unbiased* scores of the selected experts,
    which is the whole point of the biased-gate contract.

``ROUTE.WEIGHT_NORMALIZE``
    ``input_view_0`` weights ``[groups, k]`` to ``output_view_0`` of the same
    shape: each group is divided by its ordered sum and multiplied by the
    numeric profile's ``scale_bits`` when that scale is non-zero (the routed
    scaling factor).  A non-positive group sum is a numeric fault.

``ROUTE.EXPERT_DISPATCH``
    ``input_view_0`` U32 expert IDs ``[groups, k]``, ``input_view_1`` the token
    rows ``[groups, width]``, ``output_view_0`` the dispatch buffer
    ``[groups * k, width]`` in ``(group, slot)`` order.  ``aux_id_0`` is the
    immediate expert count every ID is checked against and is mandatory: an
    engine that cannot state the bound cannot prove the ID is inside it.

``ROUTE.INDEX_TOPK``
    Lightning-indexer selection, and -- amendment A19 -- the join that puts its
    result into the KV row space.  ``input_view_0`` index scores
    ``[span, candidates]``, or -- amendment A20 -- ``NO_ID`` for the **dense**
    form, which takes every candidate the causal rule admits instead of the top
    ``k`` by score; ``input_view_1`` the sliding-window index block
    ``[span, window]`` U32 this selection is joined to, or ``NO_ID`` for no
    join; ``input_view_2`` a one-element U32 view naming the **compression
    ratio** of the candidate axis, or ``NO_ID`` for an uncompressed axis;
    ``input_view_3`` -- amendment AM-E10 -- the candidate admission plane
    ``[span, candidates]`` a ``ROUTE.CANDIDATE_MASK`` wrote, or ``NO_ID`` for an
    unrestricted axis, in which case every check, count and result is what it
    was before the slot existed.
    ``output_view_0`` U32 KV rows ``[span, window + k]``, **compacted and
    sorted ascending**, tail-padded with ``0xffffffff``, so that
    ATTENTION.SPARSE gathers in address order and never executes a pad.
    ``aux_id_0`` immediate ``k`` (``NO_ID`` uses the output extent), which with
    ``in0`` absent is the **capacity** of the compressed segment rather than a
    selection width; ``aux_id_1`` mask mode (``0`` causal, ``1`` full),
    ``aux_id_2`` the runtime symbol bounding the context **in the symbol's own
    units**, ``aux_id_3`` the symbol holding the absolute position of query
    ``0``, in the same units.  A prefill that is physically streamed one row at
    a time recovers that row's logical position from the joined prefill window;
    decode keeps ``aux_id_3`` authoritative because its window operand contains
    physical circular-buffer rows, not time coordinates.

    With a compression ratio ``r`` the candidate axis holds ``context // r``
    groups, group ``g`` completes at absolute position ``r * (g + 1) - 1``, and
    a causal query at absolute position ``p`` therefore sees ``(p + 1) // r`` of
    them -- which is the released ``Indexer``'s mask in prefill and its whole
    cache in decode, from one rule rather than two branches.  A selected group
    ``g`` is rebased onto the phase's actual KV layout: prefill begins the
    compressed segment after all current rows, while decode begins it after the
    fixed circular-window capacity.  There is never a phase whose sparse KV
    operand contains both current rows and a second copy of the window.

    Amendment AM-E10 restricts *which* candidates the horizon admits without
    changing what selection means.  An admission plane in ``in3`` removes the
    columns its flag clears from consideration; ranking, rebasing, joining,
    compaction and the tie break are untouched, and with the slot absent the
    operator is the one that shipped.  The plane is an operand rather than a
    rewritten score because the score this device can hold is finite: masking a
    column to minus infinity would still let a selection *return* that column
    once fewer than ``k`` columns are admitted, and a returned candidate is a KV
    row that gets attended.  Exclusion cannot do that, and the two readings
    agree exactly whenever at least ``k`` columns are admitted.

    That horizon is the *whole* of the dense form.  ``Indexer.forward`` is
    ``get_compress_topk_idxs`` with a ranking in front of it: both count groups
    with ``(p + 1) // r``, both add the same ``offset``, and both end at the
    same concatenation in ``Attention.forward``.  So the dense path is this
    operator with ``in0`` removed, and the span it can no longer read off the
    score view it reads off ``output_view_0`` instead.

``ROUTE.BLOCK_MAX``
    Amendment AM-E10, the first half of the candidate pool.  ``input_view_0``
    index scores ``[span, candidates]`` (or ``[candidates]``),
    ``output_view_0`` one score per block ``[span, blocks]``, ``aux_id_0`` the
    **mandatory** immediate block width.  ``blocks`` must be exactly the number
    of blocks the candidate axis has at that width, tail included, so a view
    pair that does not tile is a descriptor fault rather than a reduction over
    whatever happens to be in range.

    A tail block shorter than the block width reduces over its own valid
    columns.  That *is* the reference's minus-infinity padding: the maximum of a
    block padded with minus infinity is the maximum of its valid entries.  The
    padding is not reproduced as a value because this device's shared narrowing
    site refuses an infinity outright, which is also why eligibility leaves this
    engine as ``ROUTE.CANDIDATE_MASK``'s flag plane rather than as a rewritten
    score.

``ROUTE.CANDIDATE_MASK``
    Amendment AM-E10, the second half.  ``input_view_0`` U32 block IDs
    ``[span, chosen]`` -- ``0xffffffff`` in a slot names no block, so a selector
    that filled fewer slots than it has needs no second shape --
    ``output_view_0`` the U8 or U32 admission plane ``[span, width]``, one flag
    per candidate position, ``1`` admitted and ``0`` not.  ``aux_id_0`` is the
    **mandatory** immediate block width, and every block ID is checked against
    the ``width``-derived block count: an ID outside it is counted in
    ``route.rejected_ids`` and faults.

    A repeated block ID is legal and idempotent, which is what makes a pinned
    block cheap for a producer to add: appending the last block's ID to a
    selection cannot change the plane if it is already there.  The pinning rule
    itself is *not* in this engine -- it belongs to whatever produces the block
    IDs -- because an operator that quietly admitted a block nobody selected
    would be unauditable.

``ROUTE.HASH_ROUTE``
    ``input_view_0`` U32/U64 keys ``[n]``, ``input_view_1`` a U32 route table
    ``[slots]``, ``output_view_0`` U32 destinations ``[n]``.  The mixing
    function is the frozen 32-bit finalizer in :func:`mix32`; it is part of the
    contract because two nodes must derive the same destination.

``ROUTE.WINDOW_INDEX``
    ``input_view_0`` U32 absolute query positions ``[span]``;
    ``output_view_0`` U32 ``[span, window]`` of the visible KV rows ending at
    each query, tail-padded with ``0xffffffff``.  In prefill those rows are
    absolute indices into the current-request KV tensor.  In decode they are
    physical slots of the circular window, in causal oldest-to-newest order.
    ``aux_id_0`` is the immediate window (``NO_ID`` uses the output extent),
    ``aux_id_1`` the mask mode, and ``aux_id_2`` the runtime symbol bounding the
    context.

``ROUTE.DSPARK_WINDOW_INDEX``
    Amendment A30.  The DSpark draft window: ``input_view_0`` U32 absolute
    query positions ``[block]`` -- the consecutive run beginning at the request
    cursor -- and ``output_view_0`` U32 ``[block, window + block]``.
    ``aux_id_0`` is the immediate window capacity and ``aux_id_1`` the
    immediate draft block size, both **mandatory**; ``aux_id_2`` is the runtime
    symbol bounding the context; ``aux_id_3`` is ``NO_ID``.  There is no mask
    mode to spend a slot on, so ``aux_id_1`` carries the block width instead --
    amendment A6's move on ``ATTENTION.SPARSE``, and the same corollary: an
    engine dispatches its operand reading on the subopcode.

    One row is computed from the cursor ``p`` and written **identically** to
    all ``block`` rows: ``arange(0, min(window, p + 1))``, the populated
    physical slots of the main circular window, followed by
    ``window + arange(0, block)``, the draft rows appended after it in a
    disjoint address range.  The broadcast is the semantics, not an
    optimisation -- attention inside the draft block is bidirectional, which is
    what makes one parallel block pass mean anything.  The order is
    slot-ascending and deliberately *not* chronological: the released helper
    does not rotate, so after saturation the history is ``0..window-1`` rather
    than the wrap ``WINDOW_INDEX`` writes.  Padding is a tail and never
    interior, reachable only while ``p + 1 < window``.

    Decode only.  ``DSparkAttention.forward`` returns after filling its cache
    when ``start_pos == 0``, so the released helper is never called in prefill
    and asserts ``start_pos > 0``; the graph agrees, carrying ``phases =
    ("decode",)``.  Prefill traps rather than reusing the decode rule, because
    silently defining a row nothing states is the substitution this operator
    exists to prevent.
"""

from __future__ import annotations

import numpy as np

from runtime.abi3.constants import DType, Major, NO_ID, Route
from runtime.abi3.descriptors import Descriptor, Phase, Symbol
from runtime.sim.engine import EngineContext, EngineError, register
from runtime.sim.engines.reduction import narrow, ordered_sum, widen
from runtime.sim.memory import ResolvedView

MASK_CAUSAL = 0
MASK_FULL = 1

PAD_INDEX = NO_ID
"""Tail padding written into an index output that has fewer entries than slots."""

#: The unsigned integer type of a storage element of each byte width, used to
#: read a score view as codes without widening it to binary32.
_UNSIGNED_OF_WIDTH = {2: np.uint16, 4: np.uint32}


def _require(condition: bool, message: str, trap_class: int = 3) -> None:
    if not condition:
        raise EngineError(message, trap_class=trap_class)


def _check_operator(descriptor: Descriptor, sub: int) -> None:
    payload = descriptor.payload
    _require(
        int(payload["engine_family"]) == int(Major.ROUTE)
        and int(payload["engine_sub"]) == int(sub),
        f"operator {descriptor.descriptor_id} does not describe "
        f"ROUTE.{Route(sub).name}",
    )


def _aux(descriptor: Descriptor, slot: int) -> int | None:
    value = int(descriptor.payload[f"aux_id_{slot}"])
    return None if value == NO_ID else value


def mix32(keys: np.ndarray) -> np.ndarray:
    """Frozen 32-bit avalanche used by ``ROUTE.HASH_ROUTE``."""
    value = np.ascontiguousarray(keys, dtype=np.uint64).astype(np.uint64)
    value = value & np.uint64(0xFFFFFFFF)
    value ^= value >> np.uint64(16)
    value = (value * np.uint64(0x85EBCA6B)) & np.uint64(0xFFFFFFFF)
    value ^= value >> np.uint64(13)
    value = (value * np.uint64(0xC2B2AE35)) & np.uint64(0xFFFFFFFF)
    value ^= value >> np.uint64(16)
    return value.astype(np.uint32)


def _groups(view: ResolvedView, label: str) -> tuple[int, int]:
    """Interpret a view as ``[groups, width]``, allowing a rank-1 single group."""
    _require(
        len(view.dims) in (1, 2),
        f"ROUTE {label} view {view.descriptor_id} has rank {len(view.dims)}, "
        "expected [groups, width] or [width]",
    )
    if len(view.dims) == 1:
        return 1, int(view.dims[0])
    return int(view.dims[0]), int(view.dims[1])


def _u32_out(view: ResolvedView, label: str) -> None:
    _require(
        view.dtype == int(DType.U32),
        f"ROUTE {label} view {view.descriptor_id} is dtype {view.dtype:#04x}, "
        "expected U32",
    )


def _rank_descending(keys: np.ndarray) -> np.ndarray:
    """Indices ordered by descending key, ties resolved to the lower index."""
    return np.argsort(-keys, axis=-1, kind="stable")


def _symbol_value(ctx: EngineContext, symbol_id: int | None, default: int) -> int:
    if symbol_id is None:
        return default
    return int(ctx.symbol(symbol_id))


# ---------------------------------------------------------------------------
# TOPK and BIASED_TOPK
# ---------------------------------------------------------------------------
def _topk(ctx: EngineContext, descriptor: Descriptor, sub: int) -> None:
    _check_operator(descriptor, sub)
    score_view = ctx.input_view(descriptor, 0)
    bias_view = (
        ctx.input_view(descriptor, 1) if sub == int(Route.BIASED_TOPK) else None
    )
    id_view = ctx.output_view(descriptor, 0)
    weight_view_id = descriptor.payload["output_view_1"]
    weight_view = None if weight_view_id == NO_ID else ctx.view(weight_view_id)
    _u32_out(id_view, "expert ID")

    groups, experts = _groups(score_view, "score")
    out_groups, slots = _groups(id_view, "expert ID")
    declared = _aux(descriptor, 0)
    topk = slots if declared is None else declared
    _require(
        out_groups == groups,
        f"ROUTE.TOPK output view {id_view.descriptor_id} covers {out_groups} "
        f"groups, expected {groups}",
    )
    _require(
        0 < topk <= experts and topk == slots,
        f"ROUTE.TOPK selects {topk} of {experts} experts into {slots} slots",
    )

    scores = widen(ctx, score_view).reshape(groups, experts)
    keys = scores
    if bias_view is not None:
        bias_groups, bias_experts = _groups(bias_view, "bias")
        _require(
            bias_experts == experts and bias_groups in (1, groups),
            f"ROUTE.BIASED_TOPK bias view {bias_view.descriptor_id} dims "
            f"{bias_view.dims} do not broadcast over {groups} x {experts}",
        )
        bias = widen(ctx, bias_view).reshape(bias_groups, experts)
        keys = np.add(scores, bias, dtype=np.float32)
    _require(
        bool(np.all(np.isfinite(keys))),
        f"ROUTE.{Route(sub).name}: the routing keys contain a NaN or infinite "
        "value",
        trap_class=6,
    )

    order = _rank_descending(keys)[:, :topk]
    ctx.write(id_view, order.astype(np.uint32).reshape(id_view.dims))
    if weight_view is not None:
        weight_groups, weight_slots = _groups(weight_view, "weight")
        _require(
            weight_groups == groups and weight_slots == topk,
            f"ROUTE.TOPK weight view {weight_view.descriptor_id} dims "
            f"{weight_view.dims} differ from {(groups, topk)}",
        )
        selected = np.take_along_axis(scores, order, axis=1)
        ctx.write(weight_view, narrow(selected, weight_view))
    ctx.counters.add("route.topk_candidates", groups * experts)
    ctx.counters.add("route.selected_experts", groups * topk)


@register(Major.ROUTE, Route.TOPK)
def topk(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _topk(ctx, descriptor, int(Route.TOPK))


@register(Major.ROUTE, Route.BIASED_TOPK)
def biased_topk(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _topk(ctx, descriptor, int(Route.BIASED_TOPK))


# ---------------------------------------------------------------------------
# WEIGHT_NORMALIZE
# ---------------------------------------------------------------------------
@register(Major.ROUTE, Route.WEIGHT_NORMALIZE)
def weight_normalize(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Route.WEIGHT_NORMALIZE))
    profile = ctx.numeric(descriptor.payload["numeric_profile_id"])
    weight_view = ctx.input_view(descriptor, 0)
    out_view = ctx.output_view(descriptor, 0)
    groups, slots = _groups(weight_view, "weight")
    _require(
        out_view.element_count == groups * slots,
        f"ROUTE.WEIGHT_NORMALIZE output view {out_view.descriptor_id} holds "
        f"{out_view.element_count} elements, expected {groups * slots}",
    )
    weights = widen(ctx, weight_view).reshape(groups, slots)
    totals = ordered_sum(
        np.ascontiguousarray(weights.T), profile.reduction_order
    ).reshape(groups)
    if not bool(np.all(np.isfinite(totals))) or bool(np.any(totals <= 0)):
        raise EngineError(
            "ROUTE.WEIGHT_NORMALIZE: a group weight sum is not positive finite; "
            "a routed gate cannot be normalised by it",
            trap_class=6,
        )
    scale = np.float32(profile.scale) if profile.scale_bits else np.float32(1.0)
    _require(
        bool(np.isfinite(scale)) and scale > 0,
        f"numeric profile {profile.descriptor_id}: routed scale bits "
        f"{profile.scale_bits:#010x} are not a positive finite binary32 value",
    )
    normalised = np.multiply(
        np.divide(weights, totals.reshape(groups, 1), dtype=np.float32),
        scale,
        dtype=np.float32,
    )
    ctx.write(out_view, narrow(normalised, out_view))
    ctx.counters.add("reduction.elements", groups * slots)
    ctx.counters.add("reduction.ordered_sums", groups)


# ---------------------------------------------------------------------------
# EXPERT_DISPATCH
# ---------------------------------------------------------------------------
@register(Major.ROUTE, Route.EXPERT_DISPATCH)
def expert_dispatch(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Route.EXPERT_DISPATCH))
    id_view = ctx.input_view(descriptor, 0)
    token_view = ctx.input_view(descriptor, 1)
    out_view = ctx.output_view(descriptor, 0)
    _u32_out(id_view, "expert ID")
    groups, slots = _groups(id_view, "expert ID")
    token_groups, width = _groups(token_view, "token")
    _require(
        token_groups == groups,
        f"ROUTE.EXPERT_DISPATCH token view {token_view.descriptor_id} covers "
        f"{token_groups} groups, expected {groups}",
    )
    _require(
        token_view.dtype == out_view.dtype,
        f"ROUTE.EXPERT_DISPATCH moves {token_view.dtype:#04x} codes into a "
        f"{out_view.dtype:#04x} view",
    )
    _require(
        out_view.dims == (groups * slots, width),
        f"ROUTE.EXPERT_DISPATCH output view {out_view.descriptor_id} dims "
        f"{out_view.dims} differ from {(groups * slots, width)}",
    )
    experts = _aux(descriptor, 0)
    _require(
        experts is not None and experts > 0,
        f"operator {descriptor.descriptor_id}: ROUTE.EXPERT_DISPATCH must "
        "declare the expert count in aux_id_0 so every ID can be bound-checked",
    )
    assert experts is not None
    ids = np.asarray(ctx.read(id_view), dtype=np.uint64).reshape(groups, slots)
    rejected = int(np.count_nonzero(ids >= np.uint64(experts)))
    if rejected:
        ctx.counters.add("route.rejected_ids", rejected)
        raise EngineError(
            f"ROUTE.EXPERT_DISPATCH: {rejected} expert ID(s) name an expert "
            f"outside the declared {experts}",
            trap_class=3,
        )
    tokens = np.array(ctx.read(token_view)).reshape(groups, width)
    dispatched = np.repeat(tokens, slots, axis=0)
    ctx.write(out_view, dispatched.reshape(out_view.dims))
    # ``output_view_1``, when bound, is the expert each dispatched *row* was
    # routed to -- the same ``(group, slot)`` order the rows are in, which is
    # the graph's ``ascending_token_then_ascending_selection``.  The routed
    # contractions downstream read exactly this vector to pick a weight slab,
    # so leaving it unwritten leaves whatever the backend's allocation put
    # there: on the ROM lane a second dispatch happens to fill the same object,
    # and on the HBM lane it is a zero-filled buffer, which routed every row of
    # every layer to expert 0 with no trap -- the IDs are legal and in bounds.
    if int(descriptor.payload["output_view_1"]) != NO_ID:
        id_out_view = ctx.output_view(descriptor, 1)
        _u32_out(id_out_view, "dispatched expert ID")
        expected = groups * slots
        _require(
            int(np.prod(id_out_view.dims)) == expected,
            f"ROUTE.EXPERT_DISPATCH expert-ID output view "
            f"{id_out_view.descriptor_id} dims {id_out_view.dims} hold "
            f"{int(np.prod(id_out_view.dims))} entries, expected {expected}",
        )
        ctx.write(
            id_out_view,
            ids.astype(np.uint32).reshape(id_out_view.dims),
        )
    ctx.counters.add(
        "route.dispatched_bytes", int(dispatched.size) * dispatched.dtype.itemsize
    )


# ---------------------------------------------------------------------------
# INDEX_TOPK and WINDOW_INDEX
# ---------------------------------------------------------------------------
def _mask_mode(descriptor: Descriptor, slot: int) -> int:
    mode = _aux(descriptor, slot)
    mode = MASK_CAUSAL if mode is None else mode
    _require(mode in (MASK_CAUSAL, MASK_FULL), f"ROUTE: unknown mask mode {mode}")
    return mode


def _phase(ctx: EngineContext, where: str) -> Phase:
    value = int(ctx.symbol(int(Symbol.PHASE)))
    _require(
        value in (int(Phase.PREFILL), int(Phase.DECODE)),
        f"{where}: runtime phase {value} is neither prefill nor decode",
    )
    return Phase(value)


@register(Major.ROUTE, Route.INDEX_TOPK)
def index_topk(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Select, rebase and join, as amendment A19 fixes the operator.

    Three things happen here that used to be three different producers'
    problems, and the released model does all three at this one boundary:

    * the causal horizon is on the **candidate** axis, and a candidate is a
      compression group, so a query at absolute position ``p`` sees
      ``(p + 1) // ratio`` of them and not ``p + 1``;
    * the selected group is a *score-view* column, and the KV row it names is
      that column plus the rows the join puts before the compressed segment;
    * the window block and the compressed block are one index array by the time
      ``sparse_attn`` sees them.

    The result is compacted and sorted so that amendment A6's ordering rule is
    something the producer satisfies rather than something the consumer hopes
    for.  Reordering is safe because the released kernel reads the array as a
    *set*: ``kernel.sparse_attn`` treats every ``-1`` slot as an absent lane at
    any position, with no ordering requirement.

    Amendment A20 makes ``in0`` optional.  With no score view there is no
    ranking, and the operator emits **every** candidate the causal rule above
    admits, in ascending group order -- which is the released
    ``get_compress_topk_idxs``.  Nothing else moves: the horizon, the rebase,
    the compaction, the order and the zero-candidate case are the same three
    lines they are for a ranked selection, because the dense family *is* this
    operator with the selection removed.

    Amendment A27 separates the request row from the physical view row.  A18
    can encode only one request-dependent extent on a view, so the HBM backend
    streams the two-dynamic-axis score plane one query at a time.  During
    prefill ``POSITION_START`` remains zero for the whole request; the final
    valid absolute index in the joined causal window therefore carries the
    query position into each one-row slice.  Decode has a nonzero
    ``POSITION_START`` and its joined window contains circular-buffer slots, so
    the explicit position symbol remains the time coordinate there.
    """
    _check_operator(descriptor, int(Route.INDEX_TOPK))
    score_view = ctx.optional_input(descriptor, 0)
    window_view = ctx.optional_input(descriptor, 1)
    ratio_view = ctx.optional_input(descriptor, 2)
    mask_view = ctx.optional_input(descriptor, 3)
    out_view = ctx.output_view(descriptor, 0)
    _u32_out(out_view, "index")
    out_span, slots = _groups(out_view, "index")
    # A20: the span comes off the score view when there is one and off the
    # output otherwise.  Both name the same number -- the operator writes one
    # row per query either way -- so the dense form loses an operand and not a
    # dimension.
    span = out_span
    width: int | None = None
    if score_view is not None:
        span, width = _groups(score_view, "index score")
        _require(
            out_span == span,
            f"ROUTE.INDEX_TOPK output view {out_view.descriptor_id} covers "
            f"{out_span} query rows, expected {span}",
        )

    # -- the joined window block (A19 in1) -------------------------------
    window = 0
    window_rows: np.ndarray | None = None
    if window_view is not None:
        _u32_out(window_view, "window index")
        window_span, window = _groups(window_view, "window index")
        _require(
            window_span == span,
            f"ROUTE.INDEX_TOPK window view {window_view.descriptor_id} covers "
            f"{window_span} query rows, expected {span}",
        )
        window_rows = np.asarray(ctx.read(window_view), dtype=np.uint64).reshape(
            span, window
        )

    declared = _aux(descriptor, 0)
    topk_count = slots - window if declared is None else declared
    _require(
        0 < topk_count and topk_count + window <= slots,
        f"ROUTE.INDEX_TOPK selects {topk_count} positions and joins a "
        f"{window}-slot window into {slots} slots",
    )

    # -- the compressed candidate axis (A19 in2) -------------------------
    ratio = 1
    if ratio_view is not None:
        _u32_out(ratio_view, "compression ratio")
        _require(
            int(ratio_view.element_count) == 1,
            f"ROUTE.INDEX_TOPK compression-ratio view "
            f"{ratio_view.descriptor_id} holds "
            f"{ratio_view.element_count} elements, expected one",
        )
        ratio = int(np.asarray(ctx.read(ratio_view), dtype=np.uint64).reshape(1)[0])
        _require(
            ratio > 0,
            f"ROUTE.INDEX_TOPK compression-ratio view "
            f"{ratio_view.descriptor_id} names ratio {ratio}; a compression "
            "ratio is at least one",
        )

    mode = _mask_mode(descriptor, 1)
    phase = _phase(ctx, "ROUTE.INDEX_TOPK")
    # ``aux_id_2`` and ``aux_id_3`` are read in the *symbol's own units*, which
    # for DeepSeek is tokens.  The candidate axis is counted in groups, so the
    # ratio is what converts between them; before A19 the two were silently the
    # same number and a compressed axis had no way to say otherwise.
    # A20: what bounds the candidate axis is the scored columns when a score
    # view states them and the compressed segment's own capacity when it does
    # not.  It is one statement either way -- you cannot name more groups than
    # there is somewhere to put them.
    capacity = topk_count if width is None else width
    context = _symbol_value(ctx, _aux(descriptor, 2), capacity * ratio)
    candidates = context // ratio
    # Zero candidates is not a fault.  A context shorter than one compression
    # group has completed no group, and the released model runs that layer as
    # pure sliding-window attention: ``get_compress_topk_idxs`` returns a
    # ``[seqlen, 0]`` block and the concatenation behind it is a no-op.  With a
    # window operand the joined result is that window, which is exactly what
    # ``sparse_attn`` receives there.
    held_by = (
        f"slots aux_id_0 gives the compressed segment of output view "
        f"{out_view.descriptor_id}"
        if score_view is None
        else f"scored columns of view {score_view.descriptor_id}"
    )
    _require(
        0 <= candidates <= capacity,
        f"ROUTE.INDEX_TOPK: a context of {context} at compression ratio "
        f"{ratio} is {candidates} candidates, outside the {capacity} "
        f"{held_by}",
    )
    _require(
        candidates > 0 or window_view is not None,
        f"ROUTE.INDEX_TOPK: a context of {context} at compression ratio "
        f"{ratio} completes no candidate and no window block is joined, so "
        "the operator has nothing to select and nothing to emit",
    )
    base = _symbol_value(ctx, _aux(descriptor, 3), context - span)
    _require(
        base >= 0 and base + span <= context,
        f"ROUTE.INDEX_TOPK: a span of {span} at absolute position {base} does "
        f"not fit in {context} positions",
    )
    # The compressed segment has a phase-dependent base in the exact source
    # layout.  Prefill attends the complete current request followed by the
    # compressed prefix.  Decode attends the fixed physical window followed by
    # that prefix.  ``context`` is the complete prefill length even when the
    # score plane is streamed as one physical query row; ``window`` is the
    # physical circular-window capacity even before all of its slots are valid.
    rebase = (
        (context if phase is Phase.PREFILL else window)
        if ratio_view is not None
        else 0
    )

    # -- the candidate admission plane (AM-E10 in3) ----------------------
    # Read after ``capacity`` is settled: the plane covers the candidate axis,
    # and what states that axis is the score view when there is one and the
    # compressed segment's own capacity when there is not.  Both numbers are
    # already derived above, so the mask adds no third statement of the same
    # extent.
    admission: np.ndarray | None = None
    if mask_view is not None:
        _require(
            mask_view.dtype in (int(DType.U8), int(DType.U32)),
            f"ROUTE.INDEX_TOPK candidate mask view {mask_view.descriptor_id} is "
            f"dtype {mask_view.dtype:#04x}, expected U8 or U32",
        )
        mask_span, mask_width = _groups(mask_view, "candidate mask")
        _require(
            mask_span == span and mask_width == capacity,
            f"ROUTE.INDEX_TOPK candidate mask view {mask_view.descriptor_id} "
            f"dims {mask_view.dims} differ from the {(span, capacity)} candidate "
            "axis this operator selects over",
        )
        admission = np.asarray(ctx.read(mask_view), dtype=np.uint64).reshape(
            span, capacity
        )
        _require(
            bool(np.all(admission <= np.uint64(1))),
            f"ROUTE.INDEX_TOPK candidate mask view {mask_view.descriptor_id} "
            "holds a value other than 0 or 1; an admission flag has no third "
            "state",
        )

    scores: np.ndarray | None = None
    if score_view is not None:
        if candidates:
            scores = widen(ctx, score_view).reshape(span, width)
            _require(
                bool(np.all(np.isfinite(scores[:, :candidates]))),
                f"ROUTE.INDEX_TOPK: index score view {score_view.descriptor_id} "
                "contains a NaN or infinite value",
                trap_class=6,
            )
        else:
            scores = np.zeros((span, int(width or 0)), dtype=np.float32)
    selected = np.full((span, slots), np.uint32(PAD_INDEX), dtype=np.uint32)
    considered = 0
    for row in range(span):
        valid_window: np.ndarray | None = None
        if window_rows is not None:
            block = window_rows[row]
            valid_window = block[block != np.uint64(PAD_INDEX)]

        query_position = base + row
        if (
            mode == MASK_CAUSAL
            and phase is Phase.PREFILL
            and valid_window is not None
        ):
            # A27: a streamed prefill retains the request's zero position base
            # on every physical one-row invocation.  WINDOW_INDEX's prefill
            # row is absolute, ascending and ends at the query, so it is the
            # carried logical coordinate.  Decode cannot use this rule: its
            # window entries are physical ring slots and may wrap.
            _require(
                bool(valid_window.size),
                f"ROUTE.INDEX_TOPK: causal prefill query {row} has an empty "
                "joined window and therefore no absolute position",
            )
            if valid_window.size > 1:
                _require(
                    bool(np.all(valid_window[1:] > valid_window[:-1])),
                    f"ROUTE.INDEX_TOPK: causal prefill query {row} has a "
                    "joined window that is not strictly ascending",
                )
            query_position = int(valid_window[-1])
            _require(
                0 <= query_position < context,
                f"ROUTE.INDEX_TOPK: causal prefill query {row} carries "
                f"absolute position {query_position}, outside {context} "
                "positions",
            )
        if mode == MASK_CAUSAL:
            limit = min((query_position + 1) // ratio, candidates)
        else:
            limit = candidates
        _require(
            0 <= limit <= candidates,
            f"ROUTE.INDEX_TOPK: query {row} at absolute position "
            f"{query_position} sees {limit} of {candidates} candidates",
        )
        # AM-E10: with a plane bound, the columns this query may select from
        # are the admitted ones inside its horizon, ascending.  Without one,
        # ``admitted`` stays None and every count and branch below is the one
        # that shipped.
        admitted: np.ndarray | None = None
        if admission is not None:
            admitted = np.nonzero(admission[row, :limit])[0].astype(np.int64)
        considered += limit if admitted is None else int(admitted.size)
        take = min(topk_count, limit if admitted is None else int(admitted.size))
        if not take:
            chosen = np.zeros(0, dtype=np.int64)
        elif admitted is not None:
            if scores is None:
                # The dense form's ascending admitted prefix: the mask removes
                # columns, it does not reorder what remains.
                chosen = admitted[:take] + rebase
            else:
                # Rank within the admitted columns and map back to the column
                # the score belonged to.  ``admitted`` is ascending, so the
                # stable descending sort still resolves a tie to the lower
                # candidate index.
                order = _rank_descending(scores[row, admitted])[:take]
                chosen = admitted[order].astype(np.int64) + rebase
        elif scores is None:
            # A20's dense case.  ``take == limit`` here -- the causal rule has
            # already been clamped to ``candidates`` and ``candidates`` cannot
            # exceed the capacity ``topk_count`` states -- so this is the whole
            # admitted prefix of the candidate axis, ascending, and the ranking
            # is the only thing that is gone.
            chosen = np.arange(take, dtype=np.int64) + rebase
        else:
            chosen = (
                _rank_descending(scores[row, :limit])[:take].astype(np.int64)
                + rebase
            )
        if valid_window is None:
            joined = chosen
        else:
            joined = np.concatenate(
                (valid_window.astype(np.int64), chosen)
            )
        _require(
            joined.size > 0,
            f"ROUTE.INDEX_TOPK: query {row} selects no KV row; an empty "
            "softmax has no defined value",
            trap_class=6,
        )
        joined.sort()
        selected[row, : joined.size] = joined.astype(np.uint32)
    ctx.write(out_view, selected.reshape(out_view.dims))
    ctx.counters.add("route.topk_candidates", considered)


# ---------------------------------------------------------------------------
# BLOCK_MAX and CANDIDATE_MASK, the candidate pool (AM-E10)
#
# The reference for both is ``runtime/reference/candidate_pool.py``: the exact
# total order on score codes for the first, and the admission plane including
# the pinned last block for the second.  This engine reproduces those semantics
# with integer operations on the operand's own codes.
# ---------------------------------------------------------------------------
#: The numeric contracts these two sub-ops execute.  ``BLOCK_MAX`` selects a
#: code and rounds nothing, so its contract names an order, not an arithmetic;
#: ``CANDIDATE_MASK`` is exact integer work with no rounding at all.
BLOCK_MAX_CONTRACT = "block_max_ordered_ieee_v1"
CANDIDATE_MASK_CONTRACT = "candidate_mask_v1"

#: ``(exponent bits, mantissa bits)`` of each score format this engine orders.
#: A table rather than a constant: the same block maximum is defined for every
#: interchange format the index scores can arrive in, and the order is derived
#: from the pair rather than from one assumed width.
_SCORE_FORMATS: dict[int, tuple[int, int]] = {
    int(DType.BF16): (8, 7),
    int(DType.FP16): (5, 10),
    int(DType.FP32): (8, 23),
}


def _monotone_keys(codes: np.ndarray, dtype: int, where: str) -> np.ndarray:
    """Map score codes onto an unsigned order isomorphic to the exact one.

    The reference orders codes by ``(tier, exact value, zero rank)`` using
    rational arithmetic.  For a sign-magnitude interchange format that order is
    exactly the order of the standard monotone transform -- negatives inverted,
    non-negatives raised above them -- which is what this returns: minus
    infinity is the least key, plus infinity the greatest, and negative zero
    sits immediately below positive zero, so ``max(-0.0, +0.0)`` selects
    ``+0.0`` as the reference requires.  Being a bijection, the winning key maps
    back to the winning *code*: this operator selects and rounds nothing.

    A NaN has no place in a total order and the candidate conventions disagree
    about it, so a NaN score is refused rather than resolved.
    """
    exponent_bits, mantissa_bits = _SCORE_FORMATS[dtype]
    width = 1 + exponent_bits + mantissa_bits
    sign = np.uint64(1) << np.uint64(width - 1)
    mask = (np.uint64(1) << np.uint64(width)) - np.uint64(1)
    raw = np.asarray(codes, dtype=np.uint64)
    exponent = (raw >> np.uint64(mantissa_bits)) & np.uint64(
        (1 << exponent_bits) - 1
    )
    mantissa = raw & np.uint64((1 << mantissa_bits) - 1)
    if bool(np.any((exponent == np.uint64((1 << exponent_bits) - 1)) & (mantissa != 0))):
        raise EngineError(
            f"{where}: a NaN score has no place in the block order, and the "
            "conventions for resolving one disagree",
            trap_class=6,
        )
    negative = (raw & sign) != np.uint64(0)
    return np.where(negative, (~raw) & mask, raw | sign).astype(np.uint64)


def _codes_from_keys(keys: np.ndarray, dtype: int) -> np.ndarray:
    """Invert :func:`_monotone_keys`."""
    exponent_bits, mantissa_bits = _SCORE_FORMATS[dtype]
    width = 1 + exponent_bits + mantissa_bits
    sign = np.uint64(1) << np.uint64(width - 1)
    mask = (np.uint64(1) << np.uint64(width)) - np.uint64(1)
    raised = (keys & sign) != np.uint64(0)
    return np.where(raised, keys & ~sign, (~keys) & mask).astype(np.uint64)


def _block_width(descriptor: Descriptor, where: str) -> int:
    """Read the mandatory immediate block width.

    Mandatory for the reason ``EXPERT_DISPATCH``'s expert count is: the block
    width is what turns a position into a block ID and back, and an engine that
    cannot state it cannot prove either direction. Deriving it from the two
    extents instead would make ``[span, 17]`` into ``[span, 3]`` mean a width of
    six with one column never read -- a tiling nobody declared.
    """
    block = _aux(descriptor, 0)
    _require(
        block is not None,
        f"operator {descriptor.descriptor_id}: {where} declares no block width "
        "in aux_id_0, so no position it names can be tied to a block",
    )
    assert block is not None
    _require(
        block > 0,
        f"{where}: block width {block} is not positive",
    )
    return int(block)


def _block_count(width: int, block: int, where: str) -> int:
    _require(
        width > 0,
        f"{where}: the candidate axis is empty",
    )
    return (width + block - 1) // block


@register(Major.ROUTE, Route.BLOCK_MAX)
def block_max(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """One score per block of the candidate axis: ``block_max_ordered_ieee_v1``.

    The block width, the candidate count and the block count are three
    parameters read from the descriptor and from the two views; none of them is
    a constant here.  The V4.1 candidate pool happens to use blocks of eight,
    and this engine has no way of knowing that.

    A short tail block reduces over its own valid columns, which *is* the
    reference's minus-infinity padding: minus infinity is the identity of the
    maximum, so a block padded with it has the maximum of its real positions.
    Minus infinity is admitted as an input too -- a masked score is exactly that
    -- and the winning code is written through unchanged, because the output
    dtype must equal the input's.  The operator selects; it does not convert,
    and it does not round.
    """
    _check_operator(descriptor, int(Route.BLOCK_MAX))
    score_view = ctx.input_view(descriptor, 0)
    out_view = ctx.output_view(descriptor, 0)
    _require(
        score_view.dtype in _SCORE_FORMATS,
        f"ROUTE.BLOCK_MAX candidate score view {score_view.descriptor_id} is "
        f"dtype {score_view.dtype:#04x}; the block order is defined on the "
        "binary16, bfloat16 and binary32 score formats",
    )
    _require(
        out_view.dtype == score_view.dtype,
        f"ROUTE.BLOCK_MAX writes {score_view.dtype:#04x} codes into a "
        f"{out_view.dtype:#04x} view; the block maximum is a selection, so a "
        "storage conversion would have to be an explicit VECTOR.CONVERT",
    )
    span, width = _groups(score_view, "candidate score")
    out_span, blocks = _groups(out_view, "block score")
    _require(
        out_span == span,
        f"ROUTE.BLOCK_MAX output view {out_view.descriptor_id} covers "
        f"{out_span} query rows, expected {span}",
    )
    block = _block_width(descriptor, "ROUTE.BLOCK_MAX")
    expected = _block_count(width, block, "ROUTE.BLOCK_MAX")
    _require(
        blocks == expected,
        f"ROUTE.BLOCK_MAX reduces {width} candidates in blocks of {block}, "
        f"which is {expected} block(s), but output view "
        f"{out_view.descriptor_id} holds {blocks}",
    )
    codes = np.ascontiguousarray(ctx.read(score_view)).reshape(span, width)
    raw = codes.view(_UNSIGNED_OF_WIDTH[codes.dtype.itemsize])
    keys = _monotone_keys(
        raw,
        score_view.dtype,
        f"ROUTE.BLOCK_MAX candidate score view {score_view.descriptor_id}",
    )
    starts = np.arange(0, width, block, dtype=np.intp)
    winners = _codes_from_keys(
        np.maximum.reduceat(keys, starts, axis=1), score_view.dtype
    )
    ctx.write(
        out_view,
        winners.astype(raw.dtype).view(codes.dtype).reshape(out_view.dims),
    )
    ctx.counters.add("route.topk_candidates", span * width)


@register(Major.ROUTE, Route.CANDIDATE_MASK)
def candidate_mask(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Selected block IDs back to a per-position admission plane.

    ``1`` admits the position and ``0`` excludes it -- the polarity the
    reference fixes from the pool's own population bound -- and the plane is
    what ``ROUTE.INDEX_TOPK`` reads in its slot 3.  ``aux_id_1``, when present,
    is the admitted-population bound of the plan's ``candidate_pool_bound``
    check, and a plane above it faults here rather than at whatever reads it.

    Four properties are the reference's, not this engine's inventions:

    * a ``0xffffffff`` slot names no block, so a selector that filled fewer
      slots than it has does not need a second output shape to say so;
    * IDs are a set: a repeated ID admits its block once and order does not
      matter, which is what makes the pinned block free to append;
    * **the last block is always admitted.**  Its block maximum was taken over
      a partially filled block whose absent tail is minus-infinity padding, so
      its score is not comparable with a full block's, and the released indexer
      is applied identically in training and inference, where the current block
      is always visible.  It is not an option;
    * a block ID outside the axis is a fault, counted first in
      ``route.rejected_ids``.  The bound is derived from this operator's own two
      numbers -- the mask width and the block width -- so it holds for any
      candidate geometry rather than for one model's.
    """
    _check_operator(descriptor, int(Route.CANDIDATE_MASK))
    id_view = ctx.input_view(descriptor, 0)
    out_view = ctx.output_view(descriptor, 0)
    _u32_out(id_view, "candidate block ID")
    _require(
        out_view.dtype in (int(DType.U8), int(DType.U32)),
        f"ROUTE.CANDIDATE_MASK output view {out_view.descriptor_id} is dtype "
        f"{out_view.dtype:#04x}, expected U8 or U32",
    )
    span, chosen = _groups(id_view, "candidate block ID")
    out_span, width = _groups(out_view, "candidate mask")
    _require(
        out_span == span,
        f"ROUTE.CANDIDATE_MASK output view {out_view.descriptor_id} covers "
        f"{out_span} query rows, expected {span}",
    )
    block = _block_width(descriptor, "ROUTE.CANDIDATE_MASK")
    blocks = _block_count(width, block, "ROUTE.CANDIDATE_MASK")
    population_bound = _aux(descriptor, 1)
    ids = np.asarray(ctx.read(id_view), dtype=np.uint64).reshape(span, chosen)
    named = ids != np.uint64(PAD_INDEX)
    outside = named & (ids >= np.uint64(blocks))
    rejected = int(np.count_nonzero(outside))
    if rejected:
        ctx.counters.add("route.rejected_ids", rejected)
        offender = int(np.max(ids[outside]))
        raise EngineError(
            f"ROUTE.CANDIDATE_MASK block ID view {id_view.descriptor_id} names "
            f"block {offender}, outside the {blocks} block(s) that {width} "
            f"candidates form at a block width of {block}",
            trap_class=3,
        )
    mask = np.zeros((span, width), dtype=out_view.numpy_dtype)
    pinned = blocks - 1
    for row in range(span):
        for identifier in sorted({int(value) for value in ids[row][named[row]]} | {pinned}):
            start = identifier * block
            mask[row, start : min(start + block, width)] = 1
    population = int(np.count_nonzero(mask))
    if population_bound is not None:
        _require(
            population <= population_bound,
            f"ROUTE.CANDIDATE_MASK admits {population} positions, above the "
            f"declared bound of {population_bound}",
        )
    ctx.write(out_view, mask.reshape(out_view.dims))
    # The admitted positions are the candidates a later selection considers,
    # which is what ``route.topk_candidates`` counts; the frozen registry has no
    # event of its own for the plane.
    ctx.counters.add("route.topk_candidates", population)


@register(Major.ROUTE, Route.WINDOW_INDEX)
def window_index(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Route.WINDOW_INDEX))
    position_view = ctx.input_view(descriptor, 0)
    out_view = ctx.output_view(descriptor, 0)
    _u32_out(out_view, "window index")
    _u32_out(position_view, "position")
    span, slots = _groups(out_view, "window index")
    declared = _aux(descriptor, 0)
    window = slots if declared is None else declared
    _require(
        0 < window <= slots,
        f"ROUTE.WINDOW_INDEX writes a {window}-position window into {slots} "
        "slots",
    )
    _require(
        position_view.element_count == span,
        f"ROUTE.WINDOW_INDEX position view {position_view.descriptor_id} holds "
        f"{position_view.element_count} positions for {span} query rows",
    )
    mode = _mask_mode(descriptor, 1)
    phase = _phase(ctx, "ROUTE.WINDOW_INDEX")
    context_symbol = _aux(descriptor, 2)
    _require(
        mode == MASK_CAUSAL or context_symbol is not None,
        "ROUTE.WINDOW_INDEX in full-visibility mode must name the context "
        "symbol in aux_id_2",
    )
    context = None if context_symbol is None else int(ctx.symbol(context_symbol))
    positions = np.asarray(ctx.read(position_view), dtype=np.int64).reshape(span)
    selected = np.full((span, slots), np.uint32(PAD_INDEX), dtype=np.uint32)
    produced = 0
    for row in range(span):
        position = int(positions[row])
        _require(
            position >= 0 and (context is None or position < context),
            f"ROUTE.WINDOW_INDEX: query {row} at absolute position {position} "
            f"is outside the {context} visible positions",
        )
        last = position if mode == MASK_CAUSAL else (context or position + 1) - 1
        first = max(0, last - window + 1)
        count = last - first + 1
        rows = np.arange(first, last + 1, dtype=np.uint64)
        if phase is Phase.DECODE:
            rows %= np.uint64(window)
        selected[row, :count] = rows.astype(np.uint32)
        produced += count
    ctx.write(out_view, selected.reshape(out_view.dims))
    ctx.counters.add("route.topk_candidates", produced)


@register(Major.ROUTE, Route.DSPARK_WINDOW_INDEX)
def dspark_window_index(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Write the DSpark draft window: populated ring slots, then the block.

    Amendment A30.  This is the released ``get_dspark_topk_idxs`` and nothing
    else::

        matrix = cat([arange(min(window_size, start_pos + 1)),
                      window_size + arange(block_size)])
        matrix.view(1, 1, -1).expand(bsz, block_size, -1)

    Four properties are the operator, and each is a place a plausible repair
    would be wrong.

    *One row, broadcast.*  The row is computed once from the request cursor and
    written to every draft query.  There is no per-row base and no per-row
    limit: every draft query sees every draft key.  A causal variant would be
    the same operator with the point removed.

    *History is ring slots, not a modulo reduction.*  ``arange(0, min(window,
    p + 1))`` names the populated physical slots directly -- before saturation
    the ring has filled linearly from slot 0, after it every slot is live, and
    the one expression covers both.  It is not a sliding interval reduced by a
    modulus, and it always contains ``p % window``, the slot the main KV append
    has just written.

    *Slot-ascending, not chronological.*  ``get_dspark_topk_idxs`` does not
    rotate, unlike ``get_window_topk_idxs``, so a saturated row is
    ``0..window-1`` rather than the chronological wrap a decode
    ``ROUTE.WINDOW_INDEX`` row carries.  Legal because amendment A6 freezes
    producer-defined source order and ``sparse_attn`` reads the row as a set --
    which is also why restoring the rotation would be invisible to any
    comparison of attention outputs, and why the order is asserted against the
    reference instead.

    *Padding is a tail.*  The two segments are contiguous and ``0xffffffff``
    runs to the end.  Interior padding, holding the draft segment at fixed
    columns while the history is short, is refused: A6 freezes tail padding and
    A19's consumer check requires padding to be a suffix.

    The window capacity and the block size are both mandatory immediates.
    ``ROUTE.WINDOW_INDEX`` may derive its window from the output's own extent;
    here that fallback would be actively wrong, because this output is
    ``window + block`` wide and a window derived from it makes every history
    index past the true capacity address a draft row.  ``slots == aux0 + aux1``
    and ``span == aux1`` are checkable identities, so they are checked.
    """
    _check_operator(descriptor, int(Route.DSPARK_WINDOW_INDEX))
    position_view = ctx.input_view(descriptor, 0)
    out_view = ctx.output_view(descriptor, 0)
    _u32_out(out_view, "dspark window index")
    _u32_out(position_view, "position")
    span, slots = _groups(out_view, "dspark window index")
    window = _aux(descriptor, 0)
    block = _aux(descriptor, 1)
    _require(
        window is not None and block is not None,
        "ROUTE.DSPARK_WINDOW_INDEX requires the window capacity in aux_id_0 "
        "and the draft block size in aux_id_1; neither may be derived from the "
        "output, whose extent is their sum",
    )
    _require(
        window > 0 and block > 0,
        f"ROUTE.DSPARK_WINDOW_INDEX declares window {window} and draft block "
        f"{block}; both are capacities and both must be positive",
    )
    _require(
        span == block and slots == window + block,
        f"ROUTE.DSPARK_WINDOW_INDEX writes {span} rows of {slots} slots for a "
        f"{block}-query draft block over a {window}-slot window; the output is "
        f"[{block}, {window + block}]",
    )
    phase = _phase(ctx, "ROUTE.DSPARK_WINDOW_INDEX")
    _require(
        phase is Phase.DECODE,
        "ROUTE.DSPARK_WINDOW_INDEX is a decode operator: the released "
        "DSparkAttention fills its cache and returns when start_pos == 0, so "
        "get_dspark_topk_idxs is never called in prefill and asserts "
        "start_pos > 0.  No prefill row is defined, and inventing one here "
        "would be the substitution this operator exists to prevent",
    )
    _require(
        position_view.element_count == span,
        f"ROUTE.DSPARK_WINDOW_INDEX position view {position_view.descriptor_id} "
        f"holds {position_view.element_count} positions for {span} draft rows",
    )
    context_symbol = _aux(descriptor, 2)
    context = None if context_symbol is None else int(ctx.symbol(context_symbol))
    positions = np.asarray(ctx.read(position_view), dtype=np.int64).reshape(span)
    cursor = int(positions[0])
    expected = cursor + np.arange(span, dtype=np.int64)
    _require(
        bool(np.array_equal(positions, expected)),
        f"ROUTE.DSPARK_WINDOW_INDEX position view {position_view.descriptor_id} "
        f"is not the consecutive run {cursor}..{cursor + span - 1} both "
        "backends build; the history length is read from row 0, so a "
        "differently built vector would silently shorten or lengthen it",
    )
    _require(
        cursor >= 1,
        f"ROUTE.DSPARK_WINDOW_INDEX: cursor {cursor} is a prefill position; "
        "the released helper asserts start_pos > 0",
    )
    # Only the cursor is bounded by the context.  The draft rows are positions
    # the request has not committed yet -- bounding them would refuse exactly
    # the speculation this operator indexes.
    _require(
        context is None or cursor < context,
        f"ROUTE.DSPARK_WINDOW_INDEX: cursor {cursor} is outside the {context} "
        "visible positions",
    )
    populated = min(window, cursor + 1)
    row = np.concatenate(
        (
            np.arange(populated, dtype=np.uint32),
            np.uint32(window) + np.arange(block, dtype=np.uint32),
        )
    )
    selected = np.full((span, slots), np.uint32(PAD_INDEX), dtype=np.uint32)
    selected[:, : row.size] = row
    ctx.write(out_view, selected.reshape(out_view.dims))
    ctx.counters.add("route.topk_candidates", span * int(row.size))


# ---------------------------------------------------------------------------
# HASH_ROUTE
# ---------------------------------------------------------------------------
@register(Major.ROUTE, Route.HASH_ROUTE)
def hash_route(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Route.HASH_ROUTE))
    key_view = ctx.input_view(descriptor, 0)
    table_view = ctx.input_view(descriptor, 1)
    out_view = ctx.output_view(descriptor, 0)
    _require(
        key_view.dtype in (int(DType.U32), int(DType.U64)),
        f"ROUTE.HASH_ROUTE key view {key_view.descriptor_id} is dtype "
        f"{key_view.dtype:#04x}, expected U32 or U64",
    )
    _u32_out(table_view, "route table")
    _u32_out(out_view, "destination")
    keys_count = int(key_view.element_count)
    slots = int(table_view.element_count)
    _require(slots > 0, "ROUTE.HASH_ROUTE: the route table is empty")
    _require(
        out_view.element_count == keys_count,
        f"ROUTE.HASH_ROUTE output view {out_view.descriptor_id} holds "
        f"{out_view.element_count} destinations for {keys_count} keys",
    )
    keys = np.asarray(ctx.read(key_view), dtype=np.uint64).reshape(keys_count)
    table = np.asarray(ctx.read(table_view), dtype=np.uint32).reshape(slots)
    destinations = table[(mix32(keys) % np.uint32(slots)).astype(np.intp)]
    ctx.write(out_view, destinations.astype(np.uint32).reshape(out_view.dims))
    ctx.counters.add("route.hash_lookups", keys_count)


__all__ = [
    "BLOCK_MAX_CONTRACT",
    "CANDIDATE_MASK_CONTRACT",
    "MASK_CAUSAL",
    "MASK_FULL",
    "PAD_INDEX",
    "biased_topk",
    "block_max",
    "candidate_mask",
    "dspark_window_index",
    "expert_dispatch",
    "hash_route",
    "index_topk",
    "mix32",
    "topk",
    "weight_normalize",
    "window_index",
]
