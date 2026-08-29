"""ATTENTION engine family: ``DENSE``, ``GQA`` and ``SPARSE``.

Two frozen numeric contracts live here, and neither is re-derived.

``DENSE`` and ``GQA`` execute ``qwen3_gqa_fp32_softmax_bf16_v1``: BF16 operands
widen to binary32, the QK product accumulates in ordered binary32, the scaled
score rounds once to BF16, the causal mask is a BF16 *addition* of ``0xff7f``,
the softmax runs in binary32 with an eight-lane blocked denominator and the
probability-times-value product accumulates in ordered binary32 before one final
BF16 rounding.  This module is the shape-generic driver over the frozen kernels
in :mod:`runtime.tensor_accelerator.attention` and
:mod:`runtime.tensor_accelerator.bf16`.

``SPARSE`` executes the DeepSeek-V4-Flash contract
``opentallas.deepseek_v4_sparse_attention_numeric.v1``, and drives
:func:`runtime.reference.sparse_attention.sparse_attention_bf16` directly:
block-64 gather with an online softmax, the score scale ``0x3d3504f3``, a
NUM-6.1 balanced 64-lane score sum, exactly one binary32-to-BF16 probability
conversion before the AV product, and the learned per-head binary32 attention
sink added to the denominator *after* every block.  Re-deriving any of that
inside the engine would create a second numeric implementation of one frozen
contract, which is exactly what ADR-003 forbids.

Operand and attribute convention (ABI 3.0 ``OPERATOR`` payload)
--------------------------------------------------------------
``SPARSE`` deliberately uses a **different** operand mapping from ``DENSE`` and
``GQA`` -- amendment A6 of ``docs/TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS``
section 4.1.  DeepSeek attends with one KV head over a fused ``[rows, 512]`` KV
tensor, so ``query, kv, indices, sink`` is exactly four operands and fits the
frozen record unchanged.  The engine therefore dispatches its operand reading on
the subopcode and refuses a ``SPARSE`` operator carrying a dense-shaped operand
set.

``DENSE`` / ``GQA``
    ``input_view_0``
        Queries, BF16, ``[span, query_heads, head_dim]``.
    ``input_view_1``
        Keys, BF16, ``[kv_rows, kv_heads, head_dim]``.
    ``input_view_2``
        Values, BF16, ``[kv_rows, kv_heads, head_dim]``.
    ``input_view_3``
        Optional U32 absolute query positions ``[span]``.
    ``output_view_0``
        Context, BF16, ``[span, query_heads, head_dim]``.
    ``aux_id_0``
        Query heads per KV head.  ``NO_ID`` derives ``query_heads // kv_heads``.
    ``aux_id_1``
        Mask mode: ``0`` causal by absolute position, ``1`` full visibility.
        ``NO_ID`` means causal.
    ``aux_id_2``
        Runtime symbol ID bounding the valid KV rows of the key/value views (a
        KV cache view spans its capacity, not its filled length).  ``NO_ID``
        uses the key view's leading extent.
    ``aux_id_3``
        Runtime symbol ID holding the absolute position of query ``0``.
        ``NO_ID`` derives ``context_length - span``.

``SPARSE``
    ``input_view_0``
        Queries, BF16, ``[span, query_heads, head_dim]``.
    ``input_view_1``
        Fused KV, BF16, ``[kv_rows, head_dim]`` -- rank 2, one KV head.
    ``input_view_2``
        Selected KV rows, U32, ``[span, slots]``, ascending and tail-padded with
        ``0xffffffff``.  Padding is never executed.
    ``input_view_3``
        Per-head attention-sink logits, FP32, ``[query_heads]``.
    ``output_view_0``
        Context, BF16, ``[span, query_heads, head_dim]``.
    ``aux_id_0``
        Group size.  One KV head means every query head is in the group, so a
        declared value must equal ``query_heads``.  ``NO_ID`` derives it.
    ``aux_id_1``
        Source block width.  The reference is frozen at 64, so a declared value
        must be 64.  ``NO_ID`` uses 64.
    ``aux_id_2``
        Runtime symbol ID bounding the valid KV rows.  ``NO_ID`` uses the KV
        view's leading extent.
    ``aux_id_3``
        Runtime symbol ID holding the absolute position of query ``0``.  It does
        not place a mask -- the index list already carries visibility -- but the
        span it implies is checked against the bounded context.

The scale is the numeric profile's ``scale_bits`` read as a binary32 pattern;
a non-positive or non-finite scale is a descriptor fault, never a default.  For
``SPARSE`` the qualified profile fixes it at ``0x3d3504f3``.

Counter semantics (frozen registry, ``runtime/sim/counters.py``)
---------------------------------------------------------------
``attention.heads``
    Head passes executed: ``span * query_heads``.
``attention.score_multiplications`` / ``attention.value_multiplications``
    Products the datapath actually formed, so a masked-but-computed lane counts
    and a sparse lane that was never gathered does not.  The sparse reference
    additionally reports the padded block lanes it executes against zero; those
    are its own accounting and are deliberately not folded into these two.
``attention.context_positions``
    Visible KV positions per query token, summed over the span (not multiplied
    by the head count).
``attention.sparse_indices``
    Executed index slots, taken from the gathered rows themselves.  Padding
    sentinels are excluded, and the count is never a planning formula.
``attention.kv_bytes_read``
    Distinct key and value bytes the KV heads read for this operator.
"""

from __future__ import annotations


import numpy as np

from runtime.abi3.constants import Attention, DType, Major, NO_ID
from runtime.abi3.descriptors import Descriptor
from runtime.reference.sparse_attention import (
    SPARSE_ATTENTION_BLOCK_SIZE,
    SparseAttentionReferenceError,
    sparse_attention_bf16,
)
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

SPARSE_PAD = -1
"""How the frozen sparse reference spells :data:`PAD_INDEX` as a signed index."""


# ---------------------------------------------------------------------------
# descriptor decoding
# ---------------------------------------------------------------------------
def _require(condition: bool, message: str, trap_class: int = 3) -> None:
    if not condition:
        raise EngineError(message, trap_class=trap_class)


def _aux(descriptor: Descriptor, slot: int) -> int | None:
    value = int(descriptor.payload[f"aux_id_{slot}"])
    return None if value == NO_ID else value


def _ranked(
    view: ResolvedView, label: str, rank: int, dtype: int = int(DType.BF16)
) -> None:
    _require(
        view.dtype == dtype,
        f"attention {label} view {view.descriptor_id} is dtype "
        f"{view.dtype:#04x}, expected {dtype:#04x}",
    )
    _require(
        len(view.dims) == rank,
        f"attention {label} view {view.descriptor_id} has rank "
        f"{len(view.dims)}, expected {rank}",
    )


def _rank3(view: ResolvedView, label: str, dtype: int = int(DType.BF16)) -> None:
    _ranked(view, label, 3, dtype)


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


def _preamble(
    ctx: EngineContext, descriptor: Descriptor, sub: int
) -> tuple[NumericProfile, np.float32]:
    """Check the operator's identity and decode its numeric contract."""
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
    return profile, _scale(profile)


def _context_bound(
    ctx: EngineContext, descriptor: Descriptor, view: ResolvedView, kv_rows: int
) -> int:
    context = _symbol_value(ctx, _aux(descriptor, 2), kv_rows)
    _require(
        0 < context <= kv_rows,
        f"attention: context length {context} is outside the {kv_rows} KV rows "
        f"addressed by view {view.descriptor_id}",
    )
    return context


# ---------------------------------------------------------------------------
# DENSE and GQA
# ---------------------------------------------------------------------------
def _execute_dense_gqa(ctx: EngineContext, descriptor: Descriptor, sub: int) -> None:
    _, scale = _preamble(ctx, descriptor, sub)

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

    context = _context_bound(ctx, descriptor, key_view, kv_rows)

    queries = ctx.read(query_view)
    keys = ctx.read(key_view)
    values = ctx.read(value_view)

    # Absolute positions exist to place the causal horizon.  Full-visibility
    # attention needs none, and must not be constrained by one.
    positions = (
        _positions(ctx, descriptor, extra_view, span, context)
        if mask_mode == MASK_CAUSAL or extra_view is not None
        else None
    )

    outputs = np.empty((span, query_heads, head_dim), dtype=np.uint16)
    visible_total = 0
    score_products = 0
    value_products = 0
    kv_elements = 0

    try:
        for token in range(span):
            if mask_mode == MASK_CAUSAL:
                assert positions is not None
                limit = int(positions[token]) + 1
            else:
                limit = context
            visible_total += limit
            kv_elements += 2 * limit * kv_heads * head_dim
            mask = np.zeros(context, dtype=np.uint16)
            mask[limit:] = np.uint16(CAUSAL_MASK_BF16_CODE)
            for head in range(query_heads):
                kv_head = head // group
                rows = np.ascontiguousarray(keys[:context, kv_head, :])
                value_rows = np.ascontiguousarray(values[:context, kv_head, :].T)
                width = context
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


# ---------------------------------------------------------------------------
# SPARSE (amendment A6)
# ---------------------------------------------------------------------------
def _execute_sparse(ctx: EngineContext, descriptor: Descriptor) -> None:
    profile, _ = _preamble(ctx, descriptor, int(Attention.SPARSE))

    query_view = ctx.input_view(descriptor, 0)
    kv_view = ctx.input_view(descriptor, 1)
    index_view = ctx.optional_input(descriptor, 2)
    sink_view = ctx.optional_input(descriptor, 3)
    out_view = ctx.output_view(descriptor, 0)

    _rank3(query_view, "query")
    _rank3(out_view, "output")
    # Amendment A6: the sparse operand set is q / fused KV / indices / sinks.
    # A dense-shaped operator puts rank-3 keys in slot 1 and rank-3 BF16 values
    # in slot 2; both are refused here rather than reinterpreted.
    _require(
        len(kv_view.dims) == 2 and kv_view.dtype == int(DType.BF16),
        f"ATTENTION.SPARSE input 1 (view {kv_view.descriptor_id}) is "
        f"{DType(kv_view.dtype).name} rank {len(kv_view.dims)}; amendment A6 "
        "requires a fused BF16 KV tensor [kv_rows, head_dim] with a single KV "
        "head, not a dense key view",
    )
    _require(
        index_view is not None,
        "ATTENTION.SPARSE input 2 is unbound; amendment A6 requires the U32 "
        "sparse index array there, not in the dense mask slot",
    )
    assert index_view is not None
    _require(
        index_view.dtype == int(DType.U32) and len(index_view.dims) == 2,
        f"ATTENTION.SPARSE input 2 (view {index_view.descriptor_id}) is "
        f"{DType(index_view.dtype).name} rank {len(index_view.dims)}; amendment "
        "A6 requires a U32 [span, slots] sparse index array",
    )
    _require(
        sink_view is not None,
        "ATTENTION.SPARSE input 3 is unbound; amendment A6 requires the "
        "per-head attention-sink logits there",
    )
    assert sink_view is not None
    _require(
        sink_view.dtype == int(DType.FP32) and len(sink_view.dims) == 1,
        f"ATTENTION.SPARSE input 3 (view {sink_view.descriptor_id}) is "
        f"{DType(sink_view.dtype).name} rank {len(sink_view.dims)}; amendment A6 "
        "requires FP32 [query_heads] attention-sink logits",
    )

    span, query_heads, head_dim = query_view.dims
    kv_rows, kv_dim = kv_view.dims
    _require(
        kv_dim == head_dim,
        f"attention head dimension {head_dim} differs from the fused KV "
        f"dimension {kv_dim}",
    )
    _require(
        out_view.dims == (span, query_heads, head_dim),
        f"attention output view {out_view.descriptor_id} dims {out_view.dims} "
        f"differ from the required {(span, query_heads, head_dim)}",
    )
    _require(
        index_view.dims[0] == span,
        f"sparse index view {index_view.descriptor_id} covers "
        f"{index_view.dims[0]} query rows, expected {span}",
    )
    _require(
        sink_view.dims[0] == query_heads,
        f"attention-sink view {sink_view.descriptor_id} holds "
        f"{sink_view.dims[0]} logits for {query_heads} query heads",
    )

    declared_group = _aux(descriptor, 0)
    group = query_heads if declared_group is None else declared_group
    _require(
        group == query_heads,
        f"ATTENTION.SPARSE attends one fused KV head, so the group size is "
        f"{query_heads}; the operator declares {group}",
    )
    declared_block = _aux(descriptor, 1)
    block = SPARSE_ATTENTION_BLOCK_SIZE if declared_block is None else declared_block
    _require(
        block == SPARSE_ATTENTION_BLOCK_SIZE,
        f"ATTENTION.SPARSE declares block width {block}; the qualified DeepSeek "
        f"contract is frozen at {SPARSE_ATTENTION_BLOCK_SIZE}",
    )

    context = _context_bound(ctx, descriptor, kv_view, kv_rows)
    base_symbol = _aux(descriptor, 3)
    if base_symbol is not None:
        base = _symbol_value(ctx, base_symbol, context - span)
        _require(
            0 <= base and base + span <= context,
            f"attention: query span {span} at absolute position {base} does not "
            f"fit in a context of {context} positions",
        )

    indices, gathered = _sparse_index_rows(ctx, index_view, span, context)
    queries = np.ascontiguousarray(ctx.read(query_view))
    fused_kv = np.ascontiguousarray(ctx.read(kv_view))[:context]
    sinks = np.ascontiguousarray(ctx.read(sink_view)).view(np.uint32)

    try:
        result = sparse_attention_bf16(
            [queries.tolist()],
            [fused_kv.tolist()],
            [int(code) for code in sinks],
            [indices],
            scale_binary32=int(profile.scale_bits),
        )
    except SparseAttentionReferenceError as exc:
        raise EngineError(
            f"sparse attention numeric contract violated: {exc}", trap_class=6
        ) from exc

    outputs = np.asarray(result.values[0], dtype=np.uint16)
    ctx.write(out_view, outputs.reshape(out_view.dims))

    counters = result.counters
    ctx.counters.add("attention.heads", span * query_heads)
    ctx.counters.add("attention.context_positions", gathered)
    ctx.counters.add(
        "attention.score_multiplications", counters.qk_valid_product_accumulates
    )
    # The AV product is formed for every gathered row of every head, exactly as
    # the QK product is.  The reference additionally executes padded block lanes
    # against zero; those are its own accounting, not products over data.
    ctx.counters.add(
        "attention.value_multiplications", counters.qk_valid_product_accumulates
    )
    ctx.counters.add("attention.kv_bytes_read", counters.selected_kv_read_bytes)
    ctx.counters.add("attention.sparse_indices", counters.valid_selected_rows)


def _sparse_index_rows(
    ctx: EngineContext,
    view: ResolvedView,
    span: int,
    context: int,
) -> tuple[list[list[int]], int]:
    """Decode a ``[span, slots]`` U32 index array into signed reference rows.

    Amendment A6 fixes the array as ascending and tail-padded with
    ``0xffffffff``.  Both properties are checked: padding that is not a suffix,
    or a descending pair, is a malformed operand rather than something to
    reinterpret.  Returns the rows in the reference's ``-1``-padded signed form
    and the number of rows actually gathered.
    """
    raw = np.asarray(ctx.read(view), dtype=np.uint64).reshape(span, view.dims[1])
    rows: list[list[int]] = []
    gathered = 0
    for token in range(span):
        row = raw[token]
        valid = row != np.uint64(PAD_INDEX)
        count = int(np.count_nonzero(valid))
        _require(
            bool(np.all(valid[:count])),
            f"sparse index view {view.descriptor_id}: query {token} interleaves "
            "padding with selected rows; amendment A6 fixes padding as a "
            "trailing run",
        )
        executed = row[:count]
        if count:
            if int(executed.max()) >= context:
                bad = int(executed.max())
                raise EngineError(
                    f"sparse index view {view.descriptor_id}: query {token} "
                    f"selects KV row {bad}, outside the {context} valid rows",
                    trap_class=3,
                )
            _require(
                bool(np.all(np.diff(executed.astype(np.int64)) >= 0)),
                f"sparse index view {view.descriptor_id}: query {token} is not "
                "ascending; amendment A6 fixes the selected rows as ascending",
            )
        _require(
            count > 0,
            f"ATTENTION.SPARSE: query {token} selects no KV row; an empty "
            "softmax has no defined value",
            trap_class=6,
        )
        gathered += count
        rows.append(
            [int(value) for value in executed]
            + [SPARSE_PAD] * (int(view.dims[1]) - count)
        )
    return rows, gathered


# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------
@register(Major.ATTENTION, Attention.DENSE)
def dense(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _execute_dense_gqa(ctx, descriptor, int(Attention.DENSE))


@register(Major.ATTENTION, Attention.GQA)
def gqa(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _execute_dense_gqa(ctx, descriptor, int(Attention.GQA))


@register(Major.ATTENTION, Attention.SPARSE)
def sparse(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _execute_sparse(ctx, descriptor)


__all__ = [
    "MASK_CAUSAL",
    "MASK_FULL",
    "PAD_INDEX",
    "SPARSE_PAD",
    "dense",
    "gqa",
    "sparse",
]
