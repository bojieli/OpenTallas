"""ROUTE engine family: expert routing, sparse index selection and windowing.

Routing is where a MoE model decides *what work exists*, so every decision here
is made from device memory and is deterministic down to the tie break.  Two
rules hold across all seven subopcodes:

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
    ratio** of the candidate axis, or ``NO_ID`` for an uncompressed axis.
    ``output_view_0`` U32 KV rows ``[span, window + k]``, **compacted and
    sorted ascending**, tail-padded with ``0xffffffff``, so that
    ATTENTION.SPARSE gathers in address order and never executes a pad.
    ``aux_id_0`` immediate ``k`` (``NO_ID`` uses the output extent), which with
    ``in0`` absent is the **capacity** of the compressed segment rather than a
    selection width; ``aux_id_1`` mask mode (``0`` causal, ``1`` full),
    ``aux_id_2`` the runtime symbol bounding the context **in the symbol's own
    units**, ``aux_id_3`` the symbol holding the absolute position of query
    ``0``, in the same units.  Amendment A27 keeps that request-level base
    when a prefill is physically streamed one row at a time: with a zero base,
    the joined causal window's last non-pad entry is the absolute position of
    the physical row.  A nonzero base remains authoritative because the window
    operand names KV rows and is not the decode time-coordinate field.

    With a compression ratio ``r`` the candidate axis holds ``context // r``
    groups, group ``g`` completes at absolute position ``r * (g + 1) - 1``, and
    a causal query at absolute position ``p`` therefore sees ``(p + 1) // r`` of
    them -- which is the released ``Indexer``'s mask in prefill and its whole
    cache in decode, from one rule rather than two branches.  A selected group
    ``g`` names KV row ``span + window + g``: the KV operand ``ATTENTION.SPARSE``
    gathers from is the request's own rows, then the window, then the compressed
    rows, so the compressed segment begins after the first two.

    That horizon is the *whole* of the dense form.  ``Indexer.forward`` is
    ``get_compress_topk_idxs`` with a ranking in front of it: both count groups
    with ``(p + 1) // r``, both add the same ``offset``, and both end at the
    same concatenation in ``Attention.forward``.  So the dense path is this
    operator with ``in0`` removed, and the span it can no longer read off the
    score view it reads off ``output_view_0`` instead.

``ROUTE.HASH_ROUTE``
    ``input_view_0`` U32/U64 keys ``[n]``, ``input_view_1`` a U32 route table
    ``[slots]``, ``output_view_0`` U32 destinations ``[n]``.  The mixing
    function is the frozen 32-bit finalizer in :func:`mix32`; it is part of the
    contract because two nodes must derive the same destination.

``ROUTE.WINDOW_INDEX``
    ``input_view_0`` U32 absolute query positions ``[span]``;
    ``output_view_0`` U32 ``[span, window]`` of the visible positions ending at
    each query, ascending and tail-padded with ``0xffffffff``.  ``aux_id_0``
    immediate window (``NO_ID`` uses the output extent), ``aux_id_1`` mask
    mode, ``aux_id_2`` the runtime symbol bounding the context.
"""

from __future__ import annotations

import numpy as np

from runtime.abi3.constants import DType, Major, NO_ID, Route
from runtime.abi3.descriptors import Descriptor
from runtime.sim.engine import EngineContext, EngineError, register
from runtime.sim.engines.reduction import narrow, ordered_sum, widen
from runtime.sim.memory import ResolvedView

MASK_CAUSAL = 0
MASK_FULL = 1

PAD_INDEX = NO_ID
"""Tail padding written into an index output that has fewer entries than slots."""


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
    ``POSITION_START``; its joined window remains a KV-row address list rather
    than the time-coordinate field, so it continues to use ``base + row``.
    """
    _check_operator(descriptor, int(Route.INDEX_TOPK))
    score_view = ctx.optional_input(descriptor, 0)
    window_view = ctx.optional_input(descriptor, 1)
    ratio_view = ctx.optional_input(descriptor, 2)
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
    # The compressed rows sit behind the request's own rows and the window in
    # the KV operand ATTENTION.SPARSE gathers from, so a selected group names a
    # KV row that far along.  With no compressed axis there is no compressed
    # segment and a candidate is already a KV row.
    rebase = span + window if ratio_view is not None else 0

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
        row_rebase = rebase
        if mode == MASK_CAUSAL and base == 0 and valid_window is not None:
            # A27: a streamed prefill retains the request's zero position base
            # on every physical one-row invocation.  WINDOW_INDEX's prefill
            # row is absolute, ascending and ends at the query, so it is the
            # carried logical coordinate.  This is deliberately restricted to
            # a zero base: after decode begins, the window is an address list
            # and aux_id_3 is the explicit time axis.
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
            # The same physical one-row slice also cannot define A19's
            # compressed-KV segment base.  That segment follows the request's
            # complete current rows and the fixed window, not the streamed
            # score view's one physical row.  ``aux_id_2`` already supplies the
            # request context, so A27 carries both logical coordinates from the
            # same request-level contract.
            if ratio_view is not None:
                row_rebase = context + window
        if mode == MASK_CAUSAL:
            limit = min((query_position + 1) // ratio, candidates)
        else:
            limit = candidates
        _require(
            0 <= limit <= candidates,
            f"ROUTE.INDEX_TOPK: query {row} at absolute position "
            f"{query_position} sees {limit} of {candidates} candidates",
        )
        considered += limit
        take = min(topk_count, limit)
        if not take:
            chosen = np.zeros(0, dtype=np.int64)
        elif scores is None:
            # A20's dense case.  ``take == limit`` here -- the causal rule has
            # already been clamped to ``candidates`` and ``candidates`` cannot
            # exceed the capacity ``topk_count`` states -- so this is the whole
            # admitted prefix of the candidate axis, ascending, and the ranking
            # is the only thing that is gone.
            chosen = np.arange(take, dtype=np.int64) + row_rebase
        else:
            chosen = (
                _rank_descending(scores[row, :limit])[:take].astype(np.int64)
                + row_rebase
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
        selected[row, :count] = np.arange(first, last + 1, dtype=np.uint32)
        produced += count
    ctx.write(out_view, selected.reshape(out_view.dims))
    ctx.counters.add("route.topk_candidates", produced)


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
    "MASK_CAUSAL",
    "MASK_FULL",
    "PAD_INDEX",
    "biased_topk",
    "expert_dispatch",
    "hash_route",
    "index_topk",
    "mix32",
    "topk",
    "weight_normalize",
    "window_index",
]
