"""ATTENTION engine family: ``DENSE``, ``GQA`` and ``SPARSE``.

The numeric contract executed here is ``qwen3_gqa_fp32_softmax_bf16_v1``: BF16
operands widen to binary32, the QK product accumulates in ordered binary32, the
scaled score rounds once to BF16, the causal mask is a BF16 *addition* of
``0xff7f``, the softmax runs in binary32 with an eight-lane blocked denominator
and the probability-times-value product accumulates in ordered binary32 before
one final BF16 rounding.

None of that arithmetic is re-derived here.  This module is the *shape-generic
driver* over the frozen kernels in :mod:`runtime.tensor_accelerator.attention`
and :mod:`runtime.tensor_accelerator.bf16`; the tests assert that an operator
descriptor carrying Qwen3 shapes reproduces ``gqa_causal_attention_bf16``
bit for bit.  Re-deriving the rounding, the exponential or the reduction order
inside the engine would create a second numeric implementation of one frozen
contract, which is exactly what ADR-003 forbids.

Operand and attribute convention (ABI 3.0 ``OPERATOR`` payload)
--------------------------------------------------------------
``input_view_0``
    Queries, BF16, ``[span, query_heads, head_dim]``.
``input_view_1``
    Keys, BF16, ``[kv_rows, kv_heads, head_dim]``.
``input_view_2``
    Values, BF16, ``[kv_rows, kv_heads, head_dim]``.
``input_view_3``
    ``DENSE`` / ``GQA``: optional U32 absolute query positions ``[span]``.
    ``SPARSE``: required U32 selected KV positions, ``[span, slots]`` (shared
    by every head) or ``[span, kv_heads, slots]``.  ``0xffffffff`` is the
    padding sentinel and is never executed.
``output_view_0``
    Context, BF16, ``[span, query_heads, head_dim]``.
``aux_id_0``
    Query heads per KV head.  ``NO_ID`` derives ``query_heads // kv_heads``.
``aux_id_1``
    Mask mode: ``0`` causal by absolute position, ``1`` full visibility.
    ``NO_ID`` means causal.
``aux_id_2``
    Runtime symbol ID bounding the valid KV rows of the key/value views (a KV
    cache view spans its capacity, not its filled length).  ``NO_ID`` uses the
    key view's leading extent.
``aux_id_3``
    Runtime symbol ID holding the absolute position of query ``0``.  ``NO_ID``
    derives ``context_length - span``.

The scale is the numeric profile's ``scale_bits`` read as a binary32 pattern;
a non-positive or non-finite scale is a descriptor fault, never a default.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from runtime.abi3.constants import Attention, DType, Major, NO_ID
from runtime.abi3.descriptors import Descriptor
from runtime.sim.engine import EngineContext, EngineError, NumericProfile, register
from runtime.sim.memory import ResolvedView
from runtime.tensor_accelerator.attention import (
    CAUSAL_MASK_BF16_CODE,
    AttentionKernelError,
)
from runtime.tensor_accelerator.attention import _decode as _widen_bf16
from runtime.tensor_accelerator.attention import _encode as _round_bf16
from runtime.tensor_accelerator.attention import _softmax_bf16 as _softmax_bf16
from runtime.tensor_accelerator.bf16 import BF16KernelError, dense_bf16_linear_bf16

MASK_CAUSAL = 0
MASK_FULL = 1

PAD_INDEX = NO_ID
"""Sentinel in a sparse index view: the slot is padding and is not executed."""


# ---------------------------------------------------------------------------
# descriptor decoding
# ---------------------------------------------------------------------------
def _require(condition: bool, message: str, trap_class: int = 3) -> None:
    if not condition:
        raise EngineError(message, trap_class=trap_class)


def _aux(descriptor: Descriptor, slot: int) -> int | None:
    value = int(descriptor.payload[f"aux_id_{slot}"])
    return None if value == NO_ID else value


def _rank3(view: ResolvedView, label: str, dtype: int = int(DType.BF16)) -> None:
    _require(
        view.dtype == dtype,
        f"attention {label} view {view.descriptor_id} is dtype "
        f"{view.dtype:#04x}, expected {dtype:#04x}",
    )
    _require(
        len(view.dims) == 3,
        f"attention {label} view {view.descriptor_id} has rank "
        f"{len(view.dims)}, expected 3",
    )


def _scale(profile: NumericProfile) -> np.float32:
    value = np.float32(profile.scale)
    _require(
        bool(np.isfinite(value)) and value > 0,
        f"numeric profile {profile.descriptor_id}: attention scale bits "
        f"{profile.scale_bits:#010x} are not a positive finite binary32 value",
    )
    return value


def _symbol_value(ctx: EngineContext, symbol_id: int | None, default: int) -> int:
    if symbol_id is None:
        return default
    return int(ctx.symbol(symbol_id))


# ---------------------------------------------------------------------------
# shared execution
# ---------------------------------------------------------------------------
def _execute(ctx: EngineContext, descriptor: Descriptor, sub: int) -> None:
    payload = descriptor.payload
    _require(
        int(payload["engine_family"]) == int(Major.ATTENTION)
        and int(payload["engine_sub"]) == int(sub),
        f"operator {descriptor.descriptor_id} does not describe "
        f"ATTENTION.{Attention(sub).name}",
    )
    profile = ctx.numeric(payload["numeric_profile_id"])
    _require(
        profile.input_dtype == int(DType.BF16)
        and profile.output_dtype == int(DType.BF16),
        f"numeric profile {profile.descriptor_id}: the attention contract is "
        "BF16 in and BF16 out",
    )
    scale = _scale(profile)

    query_view = ctx.input_view(descriptor, 0)
    key_view = ctx.input_view(descriptor, 1)
    value_view = ctx.input_view(descriptor, 2)
    extra_view = ctx.optional_input(descriptor, 3)
    out_view = ctx.output_view(descriptor, 0)
    _rank3(query_view, "query")
    _rank3(key_view, "key")
    _rank3(value_view, "value")
    _rank3(out_view, "output")

    span, query_heads, head_dim = query_view.dims
    kv_rows, kv_heads, kv_dim = key_view.dims
    _require(
        value_view.dims == key_view.dims,
        f"attention value view {value_view.descriptor_id} dims "
        f"{value_view.dims} differ from the key view {key_view.dims}",
    )
    _require(
        kv_dim == head_dim,
        f"attention head dimension {head_dim} differs from the KV dimension "
        f"{kv_dim}",
    )
    _require(
        out_view.dims == (span, query_heads, head_dim),
        f"attention output view {out_view.descriptor_id} dims {out_view.dims} "
        f"differ from the required {(span, query_heads, head_dim)}",
    )

    declared_group = _aux(descriptor, 0)
    _require(
        query_heads % kv_heads == 0,
        f"attention: {query_heads} query heads do not divide into {kv_heads} "
        "KV heads",
    )
    group = query_heads // kv_heads if declared_group is None else declared_group
    _require(
        group >= 1 and group * kv_heads == query_heads,
        f"attention: declared group size {group} is inconsistent with "
        f"{query_heads} query heads over {kv_heads} KV heads",
    )
    if sub == int(Attention.DENSE):
        _require(
            group == 1,
            "ATTENTION.DENSE requires one query head per KV head; use "
            "ATTENTION.GQA for a grouped head map",
        )

    mask_mode = _aux(descriptor, 1)
    mask_mode = MASK_CAUSAL if mask_mode is None else mask_mode
    _require(
        mask_mode in (MASK_CAUSAL, MASK_FULL),
        f"attention: unknown mask mode {mask_mode}",
    )

    context = _symbol_value(ctx, _aux(descriptor, 2), kv_rows)
    _require(
        0 < context <= kv_rows,
        f"attention: context length {context} is outside the {kv_rows} KV rows "
        f"addressed by view {key_view.descriptor_id}",
    )

    queries = ctx.read(query_view)
    keys = ctx.read(key_view)
    values = ctx.read(value_view)

    if sub == int(Attention.SPARSE):
        _require(
            extra_view is not None,
            "ATTENTION.SPARSE requires a sparse index view in input slot 3",
        )
        assert extra_view is not None
        indices = _sparse_indices(ctx, extra_view, span, kv_heads, context)
        positions = None
    else:
        indices = None
        positions = _positions(ctx, descriptor, extra_view, span, context)

    outputs = np.empty((span, query_heads, head_dim), dtype=np.uint16)
    visible_total = 0
    executed_indices = 0
    score_products = 0
    value_products = 0
    kv_elements = 0

    try:
        for token in range(span):
            if indices is None:
                assert positions is not None
                limit = (
                    int(positions[token]) + 1 if mask_mode == MASK_CAUSAL else context
                )
                visible_total += limit
                kv_elements += 2 * limit * kv_heads * head_dim
                mask = np.zeros(context, dtype=np.uint16)
                mask[limit:] = np.uint16(CAUSAL_MASK_BF16_CODE)
            else:
                mask = None
            for head in range(query_heads):
                kv_head = head // group
                first_of_kv_head = head % group == 0
                if indices is None:
                    rows = np.ascontiguousarray(keys[:context, kv_head, :])
                    value_rows = np.ascontiguousarray(values[:context, kv_head, :].T)
                    width = context
                else:
                    index_rows = indices[token]
                    row_index = kv_head if len(index_rows) > 1 else 0
                    selected = index_rows[row_index]
                    width = int(selected.size)
                    _require(
                        width > 0,
                        f"ATTENTION.SPARSE: query {token} head {head} selects no "
                        "KV row; an empty softmax has no defined value",
                        trap_class=6,
                    )
                    rows = np.ascontiguousarray(keys[selected, kv_head, :])
                    value_rows = np.ascontiguousarray(values[selected, kv_head, :].T)
                    if first_of_kv_head:
                        # Every KV head reads its own gathered rows.
                        kv_elements += 2 * width * head_dim
                        if len(index_rows) > 1 or kv_head == 0:
                            # One accounting event per distinct executed index
                            # list, taken from the executed rows themselves.
                            executed_indices += width
                            visible_total += width
                score_products += width * head_dim
                value_products += width * head_dim
                scored = dense_bf16_linear_bf16(
                    np.ascontiguousarray(queries[token, head])[None, :],
                    rows,
                    input_tile_rows=1,
                    output_tile_rows=64,
                )
                scaled, _ = _round_bf16(
                    np.multiply(_widen_bf16(scored.values[0]), scale, dtype=np.float32)
                )
                if mask is not None:
                    scaled, _ = _round_bf16(
                        np.add(
                            _widen_bf16(scaled),
                            _widen_bf16(mask),
                            dtype=np.float32,
                        )
                    )
                probabilities, _ = _softmax_bf16(scaled)
                context_row = dense_bf16_linear_bf16(
                    probabilities[None, :],
                    value_rows,
                    input_tile_rows=1,
                    output_tile_rows=head_dim,
                )
                outputs[token, head] = context_row.values[0]
    except (AttentionKernelError, BF16KernelError) as exc:
        raise EngineError(
            f"attention numeric contract violated: {exc}", trap_class=6
        ) from exc

    ctx.write(out_view, outputs)
    ctx.counters.add("attention.heads", span * query_heads)
    ctx.counters.add("attention.context_positions", visible_total)
    ctx.counters.add("attention.score_multiplications", score_products)
    ctx.counters.add("attention.value_multiplications", value_products)
    ctx.counters.add("attention.kv_bytes_read", kv_elements * 2)
    if indices is not None:
        ctx.counters.add("attention.sparse_indices", executed_indices)


def _positions(
    ctx: EngineContext,
    descriptor: Descriptor,
    view: ResolvedView | None,
    span: int,
    context: int,
) -> np.ndarray:
    """Absolute position of every query token, from a view or the symbol map."""
    if view is not None:
        _require(
            view.dtype == int(DType.U32),
            f"attention position view {view.descriptor_id} must be U32",
        )
        _require(
            view.element_count == span,
            f"attention position view {view.descriptor_id} holds "
            f"{view.element_count} positions for {span} query tokens",
        )
        positions = np.asarray(ctx.read(view), dtype=np.uint64).reshape(span)
    else:
        base = _symbol_value(ctx, _aux(descriptor, 3), context - span)
        _require(
            base >= 0,
            f"attention: query span {span} does not fit in a context of "
            f"{context} positions",
        )
        positions = np.arange(base, base + span, dtype=np.uint64)
    for token in range(span):
        _require(
            int(positions[token]) < context,
            f"attention: query {token} is at absolute position "
            f"{int(positions[token])}, outside the {context} visible KV rows",
        )
    return positions


def _sparse_indices(
    ctx: EngineContext,
    view: ResolvedView,
    span: int,
    kv_heads: int,
    context: int,
) -> list[list[np.ndarray]]:
    """Decode and range-check the executed sparse index list per query row."""
    _require(
        view.dtype == int(DType.U32),
        f"sparse index view {view.descriptor_id} must be U32",
    )
    _require(
        len(view.dims) in (2, 3),
        f"sparse index view {view.descriptor_id} has rank {len(view.dims)}, "
        "expected [span, slots] or [span, kv_heads, slots]",
    )
    raw = np.asarray(ctx.read(view), dtype=np.uint64)
    if len(view.dims) == 2:
        _require(
            view.dims[0] == span,
            f"sparse index view {view.descriptor_id} covers {view.dims[0]} query "
            f"rows, expected {span}",
        )
        raw = raw.reshape(span, 1, view.dims[1])
    else:
        _require(
            view.dims[0] == span and view.dims[1] == kv_heads,
            f"sparse index view {view.descriptor_id} dims {view.dims} do not "
            f"match [{span}, {kv_heads}, slots]",
        )
    out: list[list[np.ndarray]] = []
    for token in range(span):
        per_head: list[np.ndarray] = []
        for group_index in range(raw.shape[1]):
            row = raw[token, group_index]
            executed = row[row != np.uint64(PAD_INDEX)]
            if executed.size and int(executed.max()) >= context:
                bad = int(executed.max())
                raise EngineError(
                    f"sparse index view {view.descriptor_id}: query {token} "
                    f"selects KV row {bad}, outside the {context} valid rows",
                    trap_class=3,
                )
            per_head.append(executed.astype(np.intp))
        out.append(per_head)
    return out


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------
@register(Major.ATTENTION, Attention.DENSE)
def dense(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _execute(ctx, descriptor, int(Attention.DENSE))


@register(Major.ATTENTION, Attention.GQA)
def gqa(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _execute(ctx, descriptor, int(Attention.GQA))


@register(Major.ATTENTION, Attention.SPARSE)
def sparse(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _execute(ctx, descriptor, int(Attention.SPARSE))


__all__ = ["MASK_CAUSAL", "MASK_FULL", "PAD_INDEX", "dense", "gqa", "sparse"]
