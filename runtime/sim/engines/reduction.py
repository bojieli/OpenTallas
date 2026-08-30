"""REDUCTION engine family.

Five frozen subopcodes, one shared rule: a reduction happens in the order the
numeric descriptor declares, never in whatever order the host library finds
convenient.  ADR-003 makes the reduction order architectural, so
``SEQUENTIAL_ASCENDING``, ``PAIRWISE_TREE`` and ``BLOCKED_ASCENDING`` are three
distinct, reproducible datapaths here, and an unknown order is a fault.

``REDUCTION.ORDERED_SUM``
    ``input_view_0`` is ``[terms, ...]``; ``input_view_1`` is an optional base
    with the output shape, which enters the ordered sum *first* (it is the
    accumulator's initial value, exactly as a partial-tile accumulator would
    be).  ``output_view_0`` is ``[...]``.

``REDUCTION.EXPERT_SUM``
    ``input_view_0`` is ``[experts, ...]`` expert contributions in ascending
    selected-slot order, ``input_view_1`` is the ``[experts]`` weight vector,
    ``input_view_2`` is an optional base (a shared-expert or residual term).
    The engine forms ``weight * contribution`` in binary32 and reduces in the
    declared order, which is what makes a MoE layer's output independent of
    expert arrival order.  Amendment A10 makes ``input_view_1`` optional: an
    operator that omits it declares the weight was applied before the
    contribution was written, which is what the released DeepSeek expert does
    ahead of its down projection.

``REDUCTION.VOCAB_GATHER``
    ``input_view_0`` is ``[partitions, width]`` of vocabulary-parallel logits,
    ``input_view_1`` an optional ``[partitions]`` U32 source-partition order.
    The output holds ``partitions * width`` elements of the same dtype.  This
    is pure movement: no conversion, no arithmetic, no reordering inside a
    partition.

``REDUCTION.GROUPED_CONCAT``
    Up to four inputs concatenated along axis 0 into ``output_view_0``.  Every
    input shares the trailing shape and the output dtype.

``REDUCTION.PARTITION_SUM``
    ``input_view_0`` is ``[partitions, ...]`` partial results and
    ``input_view_1`` an optional base.  ``aux_id_0`` names the runtime symbol
    holding the number of *active* partitions (normally
    ``VOCABULARY_PARTITIONS`` or ``NODE_COUNT``); ``NO_ID`` reduces every
    declared partition.  A symbol wider than the view is a fault, never a clamp.
"""

from __future__ import annotations

import numpy as np

from runtime.abi3.constants import (
    DType,
    Major,
    NO_ID,
    Reduction,
    ReductionOrder,
)
from runtime.abi3.descriptors import Descriptor
from runtime.sim import formats
from runtime.sim.backend import CONTRACT_DEEPSEEK_EXPERT_SUM, declared_contract
from runtime.sim.engine import EngineContext, EngineError, register
from runtime.sim.memory import ResolvedView

MAX_INPUTS = 4


def _require(condition: bool, message: str, trap_class: int = 3) -> None:
    if not condition:
        raise EngineError(message, trap_class=trap_class)


def _check_operator(descriptor: Descriptor, sub: int) -> None:
    payload = descriptor.payload
    _require(
        int(payload["engine_family"]) == int(Major.REDUCTION)
        and int(payload["engine_sub"]) == int(sub),
        f"operator {descriptor.descriptor_id} does not describe "
        f"REDUCTION.{Reduction(sub).name}",
    )


def _aux(descriptor: Descriptor, slot: int) -> int | None:
    value = int(descriptor.payload[f"aux_id_{slot}"])
    return None if value == NO_ID else value


# ---------------------------------------------------------------------------
# numeric helpers
# ---------------------------------------------------------------------------
def widen(ctx: EngineContext, view: ResolvedView) -> np.ndarray:
    """Read a view as binary32 through the shared conversion site."""
    codes = ctx.read(view)
    if view.dtype not in formats.WIDENABLE:
        raise EngineError(
            f"view {view.descriptor_id} is dtype {view.dtype:#04x}, which has "
            "no binary32 widening",
            trap_class=3,
        )
    try:
        return formats.widen(view.dtype, codes)
    except formats.FormatError as exc:
        raise EngineError(str(exc), trap_class=3) from exc


def narrow(values: np.ndarray, view: ResolvedView) -> np.ndarray:
    """Round binary32 results once into the output view's storage dtype."""
    if view.dtype not in formats.NARROWABLE:
        raise EngineError(
            f"output view {view.descriptor_id} is dtype {view.dtype:#04x}, "
            "which is not a narrowing target",
            trap_class=3,
        )
    if not bool(np.all(np.isfinite(np.asarray(values, dtype=np.float32)))):
        raise EngineError(
            f"view {view.descriptor_id}: the reduction produced a NaN or "
            "infinite value",
            trap_class=6,
        )
    try:
        rounded, _ = formats.narrow(view.dtype, values)
    except formats.FormatError as exc:
        raise EngineError(str(exc), trap_class=6) from exc
    return rounded.reshape(view.dims)


def ordered_sum(stack: np.ndarray, order: int) -> np.ndarray:
    """Reduce ``stack`` along axis 0 in the architectural reduction order."""
    values = np.ascontiguousarray(stack, dtype=np.float32)
    terms = int(values.shape[0])
    if terms == 1:
        return values[0].copy()
    if order == int(ReductionOrder.SEQUENTIAL_ASCENDING):
        return np.add.accumulate(values, axis=0, dtype=np.float32)[-1]
    if order == int(ReductionOrder.PAIRWISE_TREE):
        current = values
        while current.shape[0] > 1:
            count = current.shape[0]
            half = count // 2
            folded = np.add(
                current[: 2 * half : 2], current[1 : 2 * half : 2], dtype=np.float32
            )
            if count % 2:
                folded = np.concatenate((folded, current[-1:]), axis=0)
            current = folded
        return current[0]
    if order == int(ReductionOrder.BLOCKED_ASCENDING):
        if terms < 8:
            return np.add.accumulate(values, axis=0, dtype=np.float32)[-1]
        lanes = values[:8].copy()
        full = terms - terms % 8
        for start in range(8, full, 8):
            lanes = np.add(lanes, values[start : start + 8], dtype=np.float32)
        tail = values[full:]
        if tail.shape[0]:
            lanes[: tail.shape[0]] = np.add(
                lanes[: tail.shape[0]], tail, dtype=np.float32
            )
        half = np.add(lanes[:4], lanes[4:], dtype=np.float32)
        quarter = np.add(half[:2], half[2:], dtype=np.float32)
        return np.add(quarter[0], quarter[1], dtype=np.float32)
    raise EngineError(
        f"numeric descriptor declares reduction order {order}, which is not in "
        "the frozen registry",
        trap_class=3,
    )


def _reduce_and_write(
    ctx: EngineContext,
    terms: np.ndarray,
    base: np.ndarray | None,
    out_view: ResolvedView,
    order: int,
    base_after_terms: bool = False,
) -> None:
    """Reduce ``terms`` in the declared order and write one rounding.

    ``TA-ABI3-OPCONV-1`` section 6 puts the optional base *first*, which is the
    residual convention: the base is one more term and it associates with the
    rest.  ``base_after_terms`` states the other placement -- reduce the terms,
    then add the base with one further binary32 addition -- because that is a
    different number rather than the same number written differently.  With
    seven leaves and a balanced tree, a base folded in as a seventh leaf meets
    the routed sum at the second level; a base added afterwards meets the
    completed sum.  The released DeepSeek expert reduction is the second, and
    the contract's name is what selects it.
    """
    stack = terms
    trailing = None
    if base is not None:
        if base_after_terms:
            trailing = base.reshape(terms.shape[1:])
        else:
            stack = np.concatenate(
                (base.reshape((1,) + terms.shape[1:]), terms), axis=0
            )
    previous = np.seterr(over="raise", invalid="raise")
    try:
        total = ordered_sum(stack, order)
        if trailing is not None:
            total = np.add(total, trailing, dtype=np.float32)
    except FloatingPointError as exc:
        raise EngineError(
            f"reduction overflowed binary32: {exc}", trap_class=6
        ) from exc
    finally:
        np.seterr(**previous)
    _require(
        total.size == out_view.element_count,
        f"reduction produced {total.size} elements for output view "
        f"{out_view.descriptor_id} of {out_view.element_count}",
    )
    ctx.write(out_view, narrow(total, out_view))
    ctx.counters.add("reduction.elements", int(stack.size))
    ctx.counters.add("reduction.ordered_sums", int(out_view.element_count))


def _leading_reduction_shapes(
    values_view: ResolvedView, out_view: ResolvedView
) -> None:
    _require(
        len(values_view.dims) >= 1 and values_view.dims[0] >= 1,
        f"reduction input view {values_view.descriptor_id} has no terms",
    )
    trailing = values_view.dims[1:]
    expected = int(np.prod(trailing)) if trailing else 1
    _require(
        out_view.element_count == expected,
        f"reduction output view {out_view.descriptor_id} holds "
        f"{out_view.element_count} elements, expected {expected}",
    )


# ---------------------------------------------------------------------------
# ORDERED_SUM and PARTITION_SUM
# ---------------------------------------------------------------------------
@register(Major.REDUCTION, Reduction.ORDERED_SUM)
def ordered_sum_engine(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Reduction.ORDERED_SUM))
    profile = ctx.numeric(descriptor.payload["numeric_profile_id"])
    values_view = ctx.input_view(descriptor, 0)
    base_view = ctx.optional_input(descriptor, 1)
    out_view = ctx.output_view(descriptor, 0)
    _leading_reduction_shapes(values_view, out_view)
    terms = widen(ctx, values_view).reshape(
        (values_view.dims[0], out_view.element_count)
    )
    base = None
    if base_view is not None:
        _require(
            base_view.element_count == out_view.element_count,
            f"reduction base view {base_view.descriptor_id} holds "
            f"{base_view.element_count} elements, expected "
            f"{out_view.element_count}",
        )
        base = widen(ctx, base_view).reshape(out_view.element_count)
    _reduce_and_write(ctx, terms, base, out_view, profile.reduction_order)


@register(Major.REDUCTION, Reduction.PARTITION_SUM)
def partition_sum(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Reduction.PARTITION_SUM))
    profile = ctx.numeric(descriptor.payload["numeric_profile_id"])
    values_view = ctx.input_view(descriptor, 0)
    base_view = ctx.optional_input(descriptor, 1)
    out_view = ctx.output_view(descriptor, 0)
    _leading_reduction_shapes(values_view, out_view)
    declared = int(values_view.dims[0])
    symbol = _aux(descriptor, 0)
    active = declared if symbol is None else int(ctx.symbol(symbol))
    _require(
        0 < active <= declared,
        f"PARTITION_SUM: {active} active partitions are outside the {declared} "
        f"declared by view {values_view.descriptor_id}",
    )
    terms = widen(ctx, values_view).reshape((declared, out_view.element_count))[
        :active
    ]
    base = None
    if base_view is not None:
        _require(
            base_view.element_count == out_view.element_count,
            f"PARTITION_SUM base view {base_view.descriptor_id} holds "
            f"{base_view.element_count} elements, expected "
            f"{out_view.element_count}",
        )
        base = widen(ctx, base_view).reshape(out_view.element_count)
    _reduce_and_write(ctx, terms, base, out_view, profile.reduction_order)


# ---------------------------------------------------------------------------
# EXPERT_SUM
# ---------------------------------------------------------------------------
@register(Major.REDUCTION, Reduction.EXPERT_SUM)
def expert_sum(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Reduction.EXPERT_SUM))
    profile = ctx.numeric(descriptor.payload["numeric_profile_id"])
    values_view = ctx.input_view(descriptor, 0)
    # Amendment A10: the weights are optional.  The released DeepSeek expert
    # multiplies by its routing weight before the down projection, so an
    # operator that leaves input_view_1 unbound is declaring that the weight
    # has already been applied -- and one that re-applied it here would square
    # it.  A weight vector that is present is still checked against the
    # contribution count.
    weight_view = ctx.optional_input(descriptor, 1)
    base_view = ctx.optional_input(descriptor, 2)
    out_view = ctx.output_view(descriptor, 0)
    _leading_reduction_shapes(values_view, out_view)
    experts = int(values_view.dims[0])
    weighted = widen(ctx, values_view).reshape((experts, out_view.element_count))
    if weight_view is not None:
        _require(
            weight_view.element_count == experts,
            f"EXPERT_SUM weight view {weight_view.descriptor_id} holds "
            f"{weight_view.element_count} weights for {experts} contributions",
        )
        weights = widen(ctx, weight_view).reshape((experts, 1))
        previous = np.seterr(over="raise", invalid="raise")
        try:
            weighted = np.multiply(weighted, weights, dtype=np.float32)
        except FloatingPointError as exc:
            raise EngineError(
                f"EXPERT_SUM weighting overflowed binary32: {exc}", trap_class=6
            ) from exc
        finally:
            np.seterr(**previous)
    base = None
    if base_view is not None:
        _require(
            base_view.element_count == out_view.element_count,
            f"EXPERT_SUM base view {base_view.descriptor_id} holds "
            f"{base_view.element_count} elements, expected "
            f"{out_view.element_count}",
        )
        base = widen(ctx, base_view).reshape(out_view.element_count)
    ctx.counters.add("route.expert_reductions", experts)
    _reduce_and_write(
        ctx,
        weighted,
        base,
        out_view,
        profile.reduction_order,
        base_after_terms=(
            declared_contract(ctx.table, descriptor.payload["numeric_profile_id"])
            == CONTRACT_DEEPSEEK_EXPERT_SUM
        ),
    )


# ---------------------------------------------------------------------------
# movement: VOCAB_GATHER and GROUPED_CONCAT
# ---------------------------------------------------------------------------
@register(Major.REDUCTION, Reduction.VOCAB_GATHER)
def vocab_gather(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Reduction.VOCAB_GATHER))
    values_view = ctx.input_view(descriptor, 0)
    order_view = ctx.optional_input(descriptor, 1)
    out_view = ctx.output_view(descriptor, 0)
    _require(
        len(values_view.dims) == 2,
        f"VOCAB_GATHER input view {values_view.descriptor_id} has rank "
        f"{len(values_view.dims)}, expected [partitions, width]",
    )
    _require(
        values_view.dtype == out_view.dtype,
        f"VOCAB_GATHER moves {values_view.dtype:#04x} codes into a "
        f"{out_view.dtype:#04x} view; a conversion is an explicit operation",
    )
    _require(
        values_view.element_count == out_view.element_count,
        f"VOCAB_GATHER input holds {values_view.element_count} elements and "
        f"output view {out_view.descriptor_id} holds {out_view.element_count}",
    )
    partitions, width = values_view.dims
    source = np.array(ctx.read(values_view))
    if order_view is None:
        gathered = source
    else:
        _require(
            order_view.dtype == int(DType.U32),
            f"VOCAB_GATHER order view {order_view.descriptor_id} must be U32",
        )
        _require(
            order_view.element_count == partitions,
            f"VOCAB_GATHER order view {order_view.descriptor_id} holds "
            f"{order_view.element_count} entries for {partitions} partitions",
        )
        order = np.asarray(ctx.read(order_view), dtype=np.uint64).reshape(partitions)
        if order.size and int(order.max()) >= partitions:
            raise EngineError(
                f"VOCAB_GATHER order view {order_view.descriptor_id} names "
                f"partition {int(order.max())} of {partitions}",
                trap_class=3,
            )
        gathered = source[order.astype(np.intp)]
    ctx.write(out_view, gathered.reshape(out_view.dims))
    ctx.counters.add("reduction.elements", partitions * width)


@register(Major.REDUCTION, Reduction.GROUPED_CONCAT)
def grouped_concat(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Reduction.GROUPED_CONCAT))
    out_view = ctx.output_view(descriptor, 0)
    parts: list[np.ndarray] = []
    rows = 0
    trailing: tuple[int, ...] | None = None
    for slot in range(MAX_INPUTS):
        view = ctx.optional_input(descriptor, slot)
        if view is None:
            continue
        _require(
            view.dtype == out_view.dtype,
            f"GROUPED_CONCAT input view {view.descriptor_id} is dtype "
            f"{view.dtype:#04x} but the output is {out_view.dtype:#04x}",
        )
        tail = tuple(view.dims[1:])
        if trailing is None:
            trailing = tail
        _require(
            tail == trailing,
            f"GROUPED_CONCAT input view {view.descriptor_id} has trailing shape "
            f"{tail}, expected {trailing}",
        )
        rows += int(view.dims[0])
        parts.append(np.array(ctx.read(view)))
    _require(bool(parts), "GROUPED_CONCAT names no input view")
    assert trailing is not None
    _require(
        out_view.dims == (rows,) + trailing,
        f"GROUPED_CONCAT output view {out_view.descriptor_id} dims "
        f"{out_view.dims} differ from the concatenation {(rows,) + trailing}",
    )
    joined = np.concatenate(parts, axis=0)
    ctx.write(out_view, joined.reshape(out_view.dims))
    ctx.counters.add("reduction.elements", int(joined.size))


__all__ = [
    "expert_sum",
    "grouped_concat",
    "narrow",
    "ordered_sum",
    "ordered_sum_engine",
    "partition_sum",
    "vocab_gather",
    "widen",
]
