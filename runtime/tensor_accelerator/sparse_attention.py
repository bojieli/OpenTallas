"""Data-bearing DeepSeek-V4-Flash sparse-attention kernel.

This module executes ``opentallas.deepseek_v4_sparse_attention_numeric.v1`` --
the contract frozen by :mod:`runtime.reference.sparse_attention` -- on NumPy
binary32 ufuncs instead of exact :class:`fractions.Fraction` scalars.  It is the
sparse counterpart of :mod:`runtime.tensor_accelerator.bf16`: the reference
stays the oracle, this is the implementation the simulator runs, and a
differential proves they agree bit for bit.

Nothing about the arithmetic moves.  What moves is *when* each of the frozen
operations is performed:

``QK``
    Every score is still ``binary32_ordered_dot`` over the full head dimension
    in strictly ascending reduction index.  The kernel walks the reduction on
    the outside and forms every ``(head, lane)`` product of one reduction index
    at a time -- the K-major schedule of
    :func:`runtime.tensor_accelerator.bf16.dense_bf16_linear_bf16`.  That
    reorders which output element is worked on when, which the contract does
    not constrain; it does not reorder any element's reduction, which the
    contract does.

``AV``
    Every output channel still accumulates its 64 lanes in ascending slot order
    after one rescale multiply.  The kernel walks the *lane* on the outside and
    updates every ``(head, channel)`` accumulator of one lane at a time.  Same
    argument: the lane loop is each element's reduction and it is untouched;
    the head and channel loops are independent outputs.

``exp``
    The contract is ``CR32(exp(x))``.  The kernel evaluates the host's binary64
    exponential, rounds it to binary32, and then *proves* that rounding by
    checking that perturbing the binary64 result by ``2**-40`` relative -- some
    four thousand times a correctly rounded binary64 exponential's own error --
    cannot change the binary32 it selects.  Any element that fails that proof is
    referred to :func:`runtime.reference.transcendental.binary32_exp_general_rne`,
    whose exact rational enclosure owes nothing to a host ``libm``.

Where the schedule cannot be proven equivalent
----------------------------------------------
``binary32_product_add`` is an exact-product, single-rounded add; ``a + b*c``
under two NumPy ufuncs rounds twice.  The two agree whenever the BF16 product
``b*c`` is exactly representable in binary32, and a BF16 times a BF16 has at
most 16 significant bits, so the product is exact unless it *underflows*: a
binary32 product of magnitude at least ``2**-126`` is always exact, and one
below that bound is the only place a second rounding can appear.  Even then the
two agree whenever the accumulator is at least ``2**-100``, because a term below
``2**-126`` is then strictly below half the accumulator's unit in the last place
and both forms return the accumulator unchanged.

The kernel therefore *detects* the one case it cannot schedule -- an
underflowing product landing in a near-zero accumulator -- and hands those query
rows, whole, to :func:`runtime.reference.sparse_attention.sparse_attention_bf16`.
Detection is by construction conservative: a cheap per-row bound on the smallest
nonzero product decides whether a step needs the precise test at all, and the
precise test is the exact condition above.  The same referral catches a
nonfinite intermediate, a nonpositive denominator, and an exponential that
overflows, so poisoned transactions raise from the reference with the reference's
own message rather than from a reimplementation of its validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from runtime.reference.sparse_attention import (
    BF16_MAX_ENCODING,
    INT32_MAX,
    SPARSE_ATTENTION_BLOCK_SIZE,
    SparseAttentionCounters,
    SparseAttentionReferenceError,
    sparse_attention_bf16,
)
from runtime.reference.transcendental import (
    TranscendentalReferenceError,
    binary32_exp_general_rne,
)


NUMERIC_CONTRACT = "opentallas.deepseek_v4_sparse_attention_numeric.v1"

#: Smallest positive *normal* binary32.  A BF16 product at or above this
#: magnitude carries at most 16 significant bits into a 24-bit significand and
#: is therefore exact; only below it can the product itself round.
_MINIMUM_NORMAL = float(np.float32(2.0) ** -126)
#: Accumulator magnitude above which a term below :data:`_MINIMUM_NORMAL` is
#: strictly below half an ulp and cannot change the accumulator, whether the
#: term was rounded or not.  ``2**-100`` leaves 24 binary places of slack.
_NEGLIGIBLE_ACCUMULATOR = float(np.float32(2.0) ** -100)
#: Largest finite binary32.  A BF16 product above it rounds to infinity even
#: though the exact sum it belongs to may still be finite.
_MAXIMUM_FINITE = float(np.finfo(np.float32).max)
#: Relative perturbation used to prove a binary64 exponential's binary32
#: rounding.  A correctly rounded binary64 exponential errs by about ``2**-53``
#: relative, so this is roughly a four-thousand-fold margin.
_EXP_PROOF_MARGIN = 2.0**-40
_EXP_PROOF_LOW = 1.0 - _EXP_PROOF_MARGIN
_EXP_PROOF_HIGH = 1.0 + _EXP_PROOF_MARGIN

#: Working-set budget, in binary32 elements, for one query-row tile.  A tile
#: holds its own ``[rows, heads, head_dim]`` output accumulator plus a product
#: buffer of the same shape, so a quarter-mega-element budget keeps both inside
#: a couple of megabytes and the accumulator cache resident across every source
#: block of that tile.
_ROW_TILE_ELEMENTS = 1 << 18

_BINARY32_ONE = np.float32(1.0)
_BINARY32_ZERO = np.float32(0.0)


class SparseAttentionKernelError(ValueError):
    """Raised when sparse-attention operands are malformed for this kernel."""


@dataclass(frozen=True)
class SparseAttentionKernelResult:
    """BF16 output, online-softmax observables, and the frozen counters.

    ``values`` is ``[span, heads, head_dim]`` BF16 encodings.  ``oracle_rows``
    names the query rows the fast schedule refused to commit and re-executed
    through the exact reference; it is diagnostic, and a bit-exact result does
    not depend on it being empty.
    """

    values: np.ndarray[Any, np.dtype[np.uint16]]
    final_max_binary32_codes: np.ndarray[Any, np.dtype[np.uint32]]
    sink_exp_binary32_codes: np.ndarray[Any, np.dtype[np.uint32]]
    final_denominator_binary32_codes: np.ndarray[Any, np.dtype[np.uint32]]
    output_saturated_element_count: int
    counters: SparseAttentionCounters
    oracle_rows: tuple[int, ...]


# ---------------------------------------------------------------------------
# encodings
# ---------------------------------------------------------------------------
def _widen(codes: np.ndarray[Any, Any]) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Widen BF16 encodings to binary32.  The conversion is exact."""

    bits = np.ascontiguousarray(codes, dtype=np.uint32) << np.uint32(16)
    return bits.view(np.float32)


def _narrow(
    values: np.ndarray[Any, np.dtype[np.float32]],
) -> tuple[np.ndarray[Any, np.dtype[np.uint16]], np.ndarray[Any, np.dtype[np.bool_]]]:
    """Apply NUM-4.2 binary32-to-BF16 RNE to a whole array.

    This is ``binary32_bits_to_bf16_rne`` elementwise, minus its refusal to
    convert a nonfinite input: a nonfinite accumulator has already referred its
    query row to the reference, which raises with the reference's own message.
    """

    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    rounded = upper + increment.astype(np.uint32)
    saturated = (rounded & np.uint32(0x7F80)) == np.uint32(0x7F80)
    rounded = np.where(
        saturated, (rounded & np.uint32(0x8000)) | np.uint32(0x7F7F), rounded
    )
    rounded = np.where((rounded & np.uint32(0x7FFF)) == 0, np.uint32(0), rounded)
    return np.ascontiguousarray(rounded, dtype=np.uint16), saturated


def _bits(values: np.ndarray[Any, np.dtype[np.float32]]) -> np.ndarray[Any, np.dtype[np.uint32]]:
    return np.ascontiguousarray(values, dtype=np.float32).view(np.uint32).copy()


# ---------------------------------------------------------------------------
# correctly rounded exponential
# ---------------------------------------------------------------------------
def exp_cr32(values: np.ndarray[Any, np.dtype[np.float32]]) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Return ``CR32(exp(x))`` elementwise for finite or ``-inf`` binary32 ``x``.

    The binary64 exponential supplies the candidate; a two-sided perturbation
    proves the binary32 it rounds to; anything unproven is referred to the exact
    reference.  An input whose exponential overflows binary32 returns positive
    infinity, which is poison and is reported as such by the caller.
    """

    source = np.ascontiguousarray(values, dtype=np.float32)
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        wide = np.exp(source.astype(np.float64))
        result = wide.astype(np.float32)
        low = (wide * _EXP_PROOF_LOW).astype(np.float32)
        high = (wide * _EXP_PROOF_HIGH).astype(np.float32)
        unproven = (low != result) | (high != result)
    if not unproven.any():
        return result

    flat_result = result.reshape(-1)
    flat_codes = source.reshape(-1).view(np.uint32)
    for index in np.flatnonzero(unproven.reshape(-1)):
        position = int(index)
        if not np.isfinite(flat_result[position]):
            continue
        try:
            exact = binary32_exp_general_rne(int(flat_codes[position]))
        except TranscendentalReferenceError:
            flat_result[position] = np.float32(np.inf)
            continue
        flat_result[position] = (
            np.array([exact], dtype=np.uint32).view(np.float32)[0]
        )
    return result


# ---------------------------------------------------------------------------
# operand validation, message-compatible with the reference
# ---------------------------------------------------------------------------
def _integer_codes(value: object, label: str, rank: int) -> np.ndarray[Any, Any]:
    raw = np.asarray(value)
    if raw.ndim != rank:
        raise SparseAttentionReferenceError(
            f"{label} must be a rectangular rank-{rank + 1} tensor"
            if rank >= 3
            else f"{label} must be rectangular on the row axis"
        )
    if raw.dtype.kind not in {"i", "u"}:
        raise SparseAttentionReferenceError(f"{label} must hold integer encodings")
    return raw


def _check_bf16(codes: np.ndarray[Any, Any], label: str, prefix: tuple[int, ...]) -> None:
    if np.any(codes < 0) or np.any(codes > BF16_MAX_ENCODING):
        flat = np.flatnonzero(
            ((codes < 0) | (codes > BF16_MAX_ENCODING)).reshape(-1)
        )[0]
        index = np.unravel_index(int(flat), codes.shape)
        location = "".join(f"[{value}]" for value in (*prefix, *index))
        raise SparseAttentionReferenceError(
            f"{label}{location} must be a 16-bit BF16 encoding"
        )
    nonfinite = (codes.astype(np.uint32) & np.uint32(0x7F80)) == np.uint32(0x7F80)
    if nonfinite.any():
        flat = int(np.flatnonzero(nonfinite.reshape(-1))[0])
        index = np.unravel_index(flat, codes.shape)
        location = "".join(f"[{value}]" for value in (*prefix, *index))
        raise SparseAttentionReferenceError(f"{label}{location} must be finite BF16")


def _check_binary32(codes: np.ndarray[Any, Any], label: str) -> None:
    if np.any(codes < 0) or np.any(codes > 0xFFFFFFFF):
        flat = int(np.flatnonzero(((codes < 0) | (codes > 0xFFFFFFFF)).reshape(-1))[0])
        raise SparseAttentionReferenceError(
            f"{label}[{flat}] must be a 32-bit binary32 encoding"
        )
    nonfinite = (
        codes.astype(np.uint32) & np.uint32(0x7F800000)
    ) == np.uint32(0x7F800000)
    if nonfinite.any():
        flat = int(np.flatnonzero(nonfinite.reshape(-1))[0])
        raise SparseAttentionReferenceError(f"{label}[{flat}] must be finite binary32")


# ---------------------------------------------------------------------------
# schedules
# ---------------------------------------------------------------------------
def _single_rounded_add(
    accumulator: np.ndarray[Any, np.dtype[np.float32]],
    left: np.ndarray[Any, np.dtype[np.float32]],
    right: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """``binary32_product_add`` itself, on binary64 with a proven rounding.

    A BF16 times a BF16 carries at most 16 significant bits, so the product is
    *exact* in binary64 whatever its exponent, and the accumulator widens
    exactly.  Their binary64 sum is then rounded to odd -- one ulp toward the
    exact residual whenever the sum was inexact and landed on an even
    significand -- before rounding to binary32.  Binary64 carries 53 bits and
    ``2 * 24 + 2 = 50``, so that composition is provably the single binary32
    rounding of the exact ``accumulator + left * right`` (Boldo and Melquiond),
    which is exactly what the contract's exact-product add performs.
    """

    wide = accumulator.astype(np.float64)
    product = left.astype(np.float64) * right.astype(np.float64)
    total = wide + product
    partial = total - wide
    residual = (wide - (total - partial)) + (product - partial)
    bits = np.ascontiguousarray(total).view(np.uint64)
    adjust = (residual != 0) & ((bits & np.uint64(1)) == np.uint64(0))
    if adjust.any():
        toward = np.where(residual > 0, np.float64(np.inf), np.float64(-np.inf))
        total = np.where(adjust, np.nextafter(total, toward), total)
    narrowed = total.astype(np.float32)
    return np.where(narrowed == 0, _BINARY32_ZERO, narrowed)


def _rounds_twice(
    accumulator: np.ndarray[Any, np.dtype[np.float32]],
    product: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.bool_]] | None:
    """Where ``a + fl(b*c)`` may differ from the contract's ``a + b*c``.

    A BF16 product carries at most 16 significant bits, so ``fl(b*c) == b*c``
    unless the product underflows below the smallest normal binary32 or
    overflows past the largest finite one.  Underflow can only matter while the
    accumulator is small enough for a term below ``2**-126`` to reach its unit
    in the last place, and it cannot matter at all when the accumulator is
    exactly zero, where both forms return the rounded product.
    """

    magnitude = np.abs(product)
    risky = magnitude < _MINIMUM_NORMAL
    np.logical_and(risky, product != 0, out=risky)
    np.logical_and(risky, accumulator != 0, out=risky)
    np.logical_and(risky, np.abs(accumulator) < _NEGLIGIBLE_ACCUMULATOR, out=risky)
    # A product past the binary32 range is infinite once rounded, but the exact
    # sum can still be finite: the accumulator is a finite binary32 and can
    # cancel the overflowing part of it.
    np.logical_or(risky, ~np.isfinite(product) & np.isfinite(accumulator), out=risky)
    if not risky.any():
        return None
    return risky


def _accumulate_scores(
    query_t: np.ndarray[Any, np.dtype[np.float32]],
    kv_t: np.ndarray[Any, np.dtype[np.float32]],
    checked: bool,
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Ordered QK reduction, scheduled K-major.

    ``query_t`` is ``[head_dim, rows, heads]`` and ``kv_t`` is
    ``[head_dim, rows, lanes]``; the result is ``[rows, heads, lanes]``.  Step
    ``d`` forms every product of reduction index ``d`` and adds it in, so each
    score still sees its own ``head_dim`` products in strictly ascending order.
    """

    reduction = int(query_t.shape[0])
    accumulator = np.multiply(
        query_t[0][:, :, None], kv_t[0][:, None, :], dtype=np.float32
    )
    # ``encode_binary32_rne`` canonicalizes every exact zero, and rounding the
    # exact product from a zero accumulator is rounding the product, so the
    # opening step needs nothing but that canonicalization.  From there a
    # binary32 sum is negative zero only when both addends are, so the
    # accumulator can never become one.
    accumulator[accumulator == 0] = _BINARY32_ZERO
    if reduction > 1:
        product = np.empty_like(accumulator)
        for index in range(1, reduction):
            np.multiply(
                query_t[index][:, :, None], kv_t[index][:, None, :], out=product
            )
            risky = _rounds_twice(accumulator, product) if checked else None
            if risky is None:
                np.add(accumulator, product, out=accumulator)
                continue
            where = np.nonzero(risky)
            repaired = _single_rounded_add(
                accumulator[where],
                query_t[index][where[0], where[1]],
                kv_t[index][where[0], where[2]],
            )
            np.add(accumulator, product, out=accumulator)
            accumulator[where] = repaired
    return accumulator


def _accumulate_context(
    accumulator: np.ndarray[Any, np.dtype[np.float32]],
    probabilities: np.ndarray[Any, np.dtype[np.float32]],
    kv_block: np.ndarray[Any, np.dtype[np.float32]],
    checked_lanes: np.ndarray[Any, np.dtype[np.bool_]],
) -> None:
    """Ordered AV accumulation, scheduled lane-major.

    ``accumulator`` is ``[rows, heads, head_dim]`` and already carries the
    block's rescale multiply.  ``probabilities`` is ``[rows, heads, lanes]``
    and ``kv_block`` is ``[rows, lanes, head_dim]``, zero on padding lanes.
    Lane ``l`` updates every ``(head, channel)`` accumulator at once, so each
    channel still accumulates its lanes in ascending slot order.
    """

    lanes = int(probabilities.shape[2])
    product = np.empty_like(accumulator)
    for lane in range(lanes):
        np.multiply(
            probabilities[:, :, lane][:, :, None],
            kv_block[:, None, lane, :],
            out=product,
        )
        risky = (
            _rounds_twice(accumulator, product)
            if bool(checked_lanes[lane])
            else None
        )
        if risky is None:
            np.add(accumulator, product, out=accumulator)
            continue
        where = np.nonzero(risky)
        repaired = _single_rounded_add(
            accumulator[where],
            probabilities[where[0], where[1], lane],
            kv_block[where[0], lane, where[2]],
        )
        np.add(accumulator, product, out=accumulator)
        accumulator[where] = repaired


def _row_minimum(values: np.ndarray[Any, np.dtype[np.float32]], axis: int) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Smallest nonzero magnitude along ``axis``; ``+inf`` when all are zero."""

    magnitude = np.abs(values.astype(np.float64))
    return np.where(magnitude > 0, magnitude, np.inf).min(axis=axis)


def _row_maximum(values: np.ndarray[Any, np.dtype[np.float32]], axis: int) -> np.ndarray[Any, np.dtype[np.float64]]:
    """Largest magnitude along ``axis``; zero when the row is empty of them."""

    return np.abs(values.astype(np.float64)).max(axis=axis)


# ---------------------------------------------------------------------------
# the kernel
# ---------------------------------------------------------------------------
def sparse_attention_bf16_codes(
    query_codes: object,
    kv_codes: object,
    attention_sink_binary32_codes: object,
    selected_indices: object,
    *,
    scale_binary32: int,
) -> SparseAttentionKernelResult:
    """Execute one governed block-64 sparse-attention transaction.

    Operands are dense encodings rather than the reference's nested sequences:
    ``[span, heads, head_dim]`` BF16 queries, ``[kv_rows, head_dim]`` BF16 fused
    KV, ``[heads]`` binary32 sink logits, and ``[span, slots]`` signed selected
    rows padded with ``-1``.  One batch; the reference's batch axis is a loop
    over independent transactions and the caller owns it.
    """

    queries = _integer_codes(query_codes, "query_bf16_codes", 3)
    span, heads, head_dim = (int(value) for value in queries.shape)
    if span == 0:
        raise SparseAttentionReferenceError(
            "query_bf16_codes must contain at least one position per batch"
        )
    if heads == 0:
        raise SparseAttentionReferenceError(
            "query_bf16_codes must contain at least one head"
        )
    if head_dim == 0:
        raise SparseAttentionReferenceError(
            "query_bf16_codes heads must contain at least one value"
        )
    _check_bf16(queries, "query_bf16_codes", (0,))

    kv = _integer_codes(kv_codes, "kv_bf16_codes", 2)
    kv_rows, kv_dim = (int(value) for value in kv.shape)
    if kv_rows == 0:
        raise SparseAttentionReferenceError(
            "kv_bf16_codes must contain at least one row per batch"
        )
    if kv_dim != head_dim:
        raise SparseAttentionReferenceError(
            f"kv_bf16_codes[0][0] must have head dimension {head_dim}"
        )
    _check_bf16(kv, "kv_bf16_codes", (0,))

    sinks = np.asarray(attention_sink_binary32_codes)
    if sinks.ndim != 1 or int(sinks.shape[0]) != heads:
        raise SparseAttentionReferenceError(
            "attention_sink_binary32_codes length must match query heads"
        )
    _check_binary32(sinks, "attention_sink_binary32_codes")

    if (
        isinstance(scale_binary32, bool)
        or not isinstance(scale_binary32, int)
        or not 0 <= scale_binary32 < 1 << 32
    ):
        raise SparseAttentionReferenceError(
            "scale_binary32 must be a 32-bit binary32 encoding"
        )
    scale_bits = np.array([scale_binary32], dtype=np.uint32)
    if int(scale_bits[0] & np.uint32(0x7F800000)) == 0x7F800000:
        raise SparseAttentionReferenceError("scale_binary32 must be finite binary32")
    scale = scale_bits.view(np.float32)[0]
    if not scale > 0:
        raise SparseAttentionReferenceError(
            "scale_binary32 must be greater than zero"
        )

    indices = np.asarray(selected_indices)
    if indices.ndim != 2 or int(indices.shape[0]) != span:
        raise SparseAttentionReferenceError(
            "selected_indices sequence length must match query_bf16_codes"
        )
    slots = int(indices.shape[1])
    if slots == 0:
        raise SparseAttentionReferenceError(
            "selected_indices must contain at least one slot"
        )
    indices = indices.astype(np.int64)
    illegal = (indices < -1) | (indices > INT32_MAX)
    if illegal.any():
        position, slot = np.unravel_index(
            int(np.flatnonzero(illegal.reshape(-1))[0]), indices.shape
        )
        raise SparseAttentionReferenceError(
            f"selected_indices[0][{position}][{slot}] must be -1 or a "
            "nonnegative INT32 index"
        )
    outside = indices >= kv_rows
    if outside.any():
        position, slot = np.unravel_index(
            int(np.flatnonzero(outside.reshape(-1))[0]), indices.shape
        )
        raise SparseAttentionReferenceError(
            f"selected_indices[0][{position}][{slot}] is outside {kv_rows} KV rows"
        )
    valid = indices >= 0
    leading = valid[:, :SPARSE_ATTENTION_BLOCK_SIZE]
    empty_first_block = ~leading.any(axis=1)
    if empty_first_block.any():
        position = int(np.flatnonzero(empty_first_block)[0])
        raise SparseAttentionReferenceError(
            f"selected_indices[0][{position}] first 64-slot source block must "
            "contain a valid KV row"
        )

    block_count = (
        slots + SPARSE_ATTENTION_BLOCK_SIZE - 1
    ) // SPARSE_ATTENTION_BLOCK_SIZE

    query_values = _widen(queries)
    kv_values = _widen(kv)
    sink_values = np.ascontiguousarray(sinks, dtype=np.uint32).view(np.float32)

    outputs = np.zeros((span, heads, head_dim), dtype=np.uint16)
    final_max = np.zeros((span, heads), dtype=np.float32)
    final_sink_exp = np.zeros((span, heads), dtype=np.float32)
    final_denominator = np.zeros((span, heads), dtype=np.float32)
    saturated_rows = np.zeros(span, dtype=np.int64)
    suspect = np.zeros(span, dtype=bool)

    # Smallest nonzero operand magnitudes bound the smallest nonzero product a
    # reduction can form, and a bound above the smallest normal binary32 proves
    # that no product in that reduction rounds.  This is per query row and per
    # KV row, so it stays a cheap test over the score shape rather than the
    # product shape.
    query_floor = _row_minimum(query_values, axis=2)
    kv_floor = _row_minimum(kv_values, axis=1)
    query_ceiling = _row_maximum(query_values, axis=2)
    kv_ceiling = _row_maximum(kv_values, axis=1)

    row_tile = max(1, min(span, _ROW_TILE_ELEMENTS // max(1, heads * head_dim)))

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore", divide="ignore")
    try:
        for tile_start in range(0, span, row_tile):
            tile_stop = min(tile_start + row_tile, span)
            _execute_tile(
                tile_start,
                tile_stop,
                query_values=query_values,
                kv_values=kv_values,
                sink_values=sink_values,
                indices=indices,
                valid=valid,
                scale=scale,
                block_count=block_count,
                slots=slots,
                query_floor=query_floor,
                kv_floor=kv_floor,
                query_ceiling=query_ceiling,
                kv_ceiling=kv_ceiling,
                outputs=outputs,
                final_max=final_max,
                final_sink_exp=final_sink_exp,
                final_denominator=final_denominator,
                saturated_rows=saturated_rows,
                suspect=suspect,
            )
    finally:
        np.seterr(**previous)

    oracle_rows = tuple(int(row) for row in np.flatnonzero(suspect))
    if oracle_rows:
        _repair_rows(
            oracle_rows,
            queries=queries,
            kv=kv,
            sinks=sinks,
            indices=indices,
            scale_binary32=scale_binary32,
            outputs=outputs,
            final_max=final_max,
            final_sink_exp=final_sink_exp,
            final_denominator=final_denominator,
            saturated_rows=saturated_rows,
        )

    counters = _counters(
        span=span,
        heads=heads,
        head_dim=head_dim,
        slots=slots,
        block_count=block_count,
        indices=indices,
        valid=valid,
    )
    return SparseAttentionKernelResult(
        values=outputs,
        final_max_binary32_codes=_bits(final_max),
        sink_exp_binary32_codes=_bits(final_sink_exp),
        final_denominator_binary32_codes=_bits(final_denominator),
        output_saturated_element_count=int(saturated_rows.sum()),
        counters=counters,
        oracle_rows=oracle_rows,
    )


def _execute_tile(
    tile_start: int,
    tile_stop: int,
    *,
    query_values: np.ndarray[Any, np.dtype[np.float32]],
    kv_values: np.ndarray[Any, np.dtype[np.float32]],
    sink_values: np.ndarray[Any, np.dtype[np.float32]],
    indices: np.ndarray[Any, np.dtype[np.int64]],
    valid: np.ndarray[Any, np.dtype[np.bool_]],
    scale: np.float32,
    block_count: int,
    slots: int,
    query_floor: np.ndarray[Any, np.dtype[np.float64]],
    kv_floor: np.ndarray[Any, np.dtype[np.float64]],
    query_ceiling: np.ndarray[Any, np.dtype[np.float64]],
    kv_ceiling: np.ndarray[Any, np.dtype[np.float64]],
    outputs: np.ndarray[Any, np.dtype[np.uint16]],
    final_max: np.ndarray[Any, np.dtype[np.float32]],
    final_sink_exp: np.ndarray[Any, np.dtype[np.float32]],
    final_denominator: np.ndarray[Any, np.dtype[np.float32]],
    saturated_rows: np.ndarray[Any, np.dtype[np.int64]],
    suspect: np.ndarray[Any, np.dtype[np.bool_]],
) -> None:
    rows = tile_stop - tile_start
    heads = int(query_values.shape[1])
    head_dim = int(query_values.shape[2])

    query_tile = query_values[tile_start:tile_stop]
    query_t = np.ascontiguousarray(query_tile.transpose(2, 0, 1))
    accumulator = np.zeros((rows, heads, head_dim), dtype=np.float32)
    sums = np.zeros((rows, heads), dtype=np.float32)
    maxima = np.zeros((rows, heads), dtype=np.float32)
    flagged = np.zeros(rows, dtype=bool)

    # An all-padding source block is a complete numeric no-op: the running
    # maximum is unchanged, the rescale is exactly one, the block sum is zero,
    # and the accumulator is multiplied by one.  Blocks past the last one any
    # row in this tile touches are therefore skipped, not approximated.
    tile_valid = valid[tile_start:tile_stop]
    active_blocks = block_count
    while active_blocks > 1:
        start = (active_blocks - 1) * SPARSE_ATTENTION_BLOCK_SIZE
        if tile_valid[:, start : start + SPARSE_ATTENTION_BLOCK_SIZE].any():
            break
        active_blocks -= 1

    for block in range(active_blocks):
        start = block * SPARSE_ATTENTION_BLOCK_SIZE
        stop = min(start + SPARSE_ATTENTION_BLOCK_SIZE, slots)
        lanes = stop - start
        block_indices = indices[tile_start:tile_stop, start:stop]
        lane_valid = tile_valid[:, start:stop]
        gather = np.where(lane_valid, block_indices, 0)
        kv_block = kv_values[gather]
        kv_block[~lane_valid] = _BINARY32_ZERO

        # -- QK ---------------------------------------------------------
        # The smallest and largest nonzero magnitudes of a query row and a KV
        # row bound every product their reduction forms.  A bound inside the
        # normal binary32 range proves that no product in that reduction rounds,
        # which is what lets the schedule use two ufuncs where the contract uses
        # one exact-product add.  This is per row pair, so it costs the score
        # shape rather than the product shape.
        lane_floor = np.where(lane_valid, kv_floor[gather], np.inf)
        lane_ceiling = np.where(lane_valid, kv_ceiling[gather], 0.0)
        exact_products = bool(
            np.all(
                query_floor[tile_start:tile_stop][:, :, None]
                * lane_floor[:, None, :]
                >= _MINIMUM_NORMAL
            )
            and np.all(
                query_ceiling[tile_start:tile_stop][:, :, None]
                * lane_ceiling[:, None, :]
                <= _MAXIMUM_FINITE
            )
        )
        kv_t = np.ascontiguousarray(kv_block.transpose(2, 0, 1))
        scores = _accumulate_scores(query_t, kv_t, not exact_products)
        np.multiply(scores, scale, out=scores)

        # -- online softmax --------------------------------------------
        masked = np.where(lane_valid[:, None, :], scores, np.float32(-np.inf))
        block_max = masked.max(axis=2)
        if block == 0:
            # ``maxima[head] is None`` in the reference holds for exactly the
            # first source block, because every head is visited in every block.
            maxima = np.where(block_max == 0, _BINARY32_ZERO, block_max)
            rescale = np.zeros((rows, heads), dtype=np.float32)
        else:
            updated = np.maximum(maxima, block_max)
            updated = np.where(updated == 0, _BINARY32_ZERO, updated)
            rescale = exp_cr32(np.ascontiguousarray(maxima - updated))
            maxima = updated

        offsets = np.where(
            lane_valid[:, None, :],
            scores - maxima[:, :, None],
            np.float32(-np.inf),
        )
        probabilities = exp_cr32(np.ascontiguousarray(offsets))

        padded = probabilities
        if lanes != SPARSE_ATTENTION_BLOCK_SIZE:
            padded = np.zeros((rows, heads, SPARSE_ATTENTION_BLOCK_SIZE), dtype=np.float32)
            padded[:, :, :lanes] = probabilities
        block_sum = _balanced_sum(padded)
        np.multiply(sums, rescale, out=sums)
        np.add(sums, block_sum, out=sums)

        probability_codes, _ = _narrow(probabilities)
        probability_values = _widen(probability_codes)

        # -- AV ---------------------------------------------------------
        np.multiply(accumulator, rescale[:, :, None], out=accumulator)
        if bool(np.any(rescale == 0)):
            # ``binary32_multiply`` canonicalizes its zero; a negative
            # accumulator scaled by an underflowed rescale would not.
            np.add(accumulator, _BINARY32_ZERO, out=accumulator)
        wide_probabilities = probability_values.astype(np.float64)
        checked_lanes = (
            (wide_probabilities * lane_floor[:, None, :] < _MINIMUM_NORMAL)
            & (probability_values != 0)
        ).any(axis=(0, 1))
        _accumulate_context(accumulator, probability_values, kv_block, checked_lanes)

        flagged |= ~np.isfinite(scores).reshape(rows, -1).all(axis=1)
        flagged |= ~np.isfinite(probabilities).reshape(rows, -1).all(axis=1)

    sink_exp = exp_cr32(
        np.ascontiguousarray(sink_values[None, :] - maxima)
    )
    denominator = np.add(sums, sink_exp)
    flagged |= ~(np.isfinite(denominator) & (denominator > 0)).all(axis=1)
    flagged |= ~np.isfinite(accumulator).reshape(rows, -1).all(axis=1)

    with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
        context = np.divide(accumulator, denominator[:, :, None])
    codes, saturated = _narrow(context)
    flagged |= ~np.isfinite(context).reshape(rows, -1).all(axis=1)

    outputs[tile_start:tile_stop] = codes
    final_max[tile_start:tile_stop] = maxima
    final_sink_exp[tile_start:tile_stop] = sink_exp
    final_denominator[tile_start:tile_stop] = denominator
    saturated_rows[tile_start:tile_stop] = saturated.reshape(rows, -1).sum(axis=1)
    suspect[tile_start:tile_stop] = flagged


def _balanced_sum(
    values: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """The canonical NUM-6.1 balanced tree over the trailing axis.

    The axis is the frozen 64-lane source block, so the tree is six exact
    pairwise levels and every addition is one binary32 RNE rounding, in the same
    association ``binary32_balanced_sum`` builds.
    """

    level = values
    width = int(level.shape[-1])
    while width > 1:
        if width & 1:
            level = np.concatenate(
                (level, np.zeros((*level.shape[:-1], 1), dtype=np.float32)), axis=-1
            )
            width += 1
        level = level.reshape(*level.shape[:-1], width // 2, 2)
        level = np.add(level[..., 0], level[..., 1])
        width //= 2
    return level[..., 0]


def _counters(
    *,
    span: int,
    heads: int,
    head_dim: int,
    slots: int,
    block_count: int,
    indices: np.ndarray[Any, np.dtype[np.int64]],
    valid: np.ndarray[Any, np.dtype[np.bool_]],
) -> SparseAttentionCounters:
    explicit_padding = int((indices == -1).sum())
    valid_selected = int(valid.sum())
    unique_selected = 0
    for row in range(span):
        selected = indices[row][valid[row]]
        unique_selected += int(np.unique(selected).size)

    output_rows = span
    block_lanes = output_rows * block_count * SPARSE_ATTENTION_BLOCK_SIZE
    implicit_tail = output_rows * (
        block_count * SPARSE_ATTENTION_BLOCK_SIZE - slots
    )
    padded_lanes = explicit_padding + implicit_tail
    return SparseAttentionCounters(
        output_rows=output_rows,
        source_blocks=output_rows * block_count,
        query_bf16_values=output_rows * heads * head_dim,
        query_bf16_read_bytes=output_rows * heads * head_dim * 2,
        attention_sink_binary32_reads=output_rows * heads,
        attention_sink_binary32_read_bytes=output_rows * heads * 4,
        logical_index_slots=output_rows * slots,
        selected_index_int32_reads=output_rows * slots,
        selected_index_read_bytes=output_rows * slots * 4,
        explicit_padding_slots=explicit_padding,
        implicit_tail_padding_lanes=implicit_tail,
        block_compute_lanes=block_lanes,
        valid_selected_rows=valid_selected,
        unique_selected_rows=unique_selected,
        duplicate_selected_rows=valid_selected - unique_selected,
        selected_kv_bf16_values=valid_selected * head_dim,
        selected_kv_read_bytes=valid_selected * head_dim * 2,
        qk_valid_product_accumulates=valid_selected * heads * head_dim,
        qk_padding_product_lanes=padded_lanes * heads * head_dim,
        score_scale_multiplies=block_lanes * heads,
        online_rescale_exp_evaluations=output_rows * block_count * heads,
        score_exp_evaluations=block_lanes * heads,
        score_reduction_adds=(
            output_rows * block_count * heads * (SPARSE_ATTENTION_BLOCK_SIZE - 1)
        ),
        online_denominator_multiplies=output_rows * block_count * heads,
        online_denominator_adds=output_rows * block_count * heads,
        probability_bf16_conversions=block_lanes * heads,
        output_rescale_multiplies=output_rows * block_count * heads * head_dim,
        av_product_accumulates=block_lanes * heads * head_dim,
        sink_exp_evaluations=output_rows * heads,
        sink_denominator_adds=output_rows * heads,
        final_binary32_divides=output_rows * heads * head_dim,
        output_bf16_conversions=output_rows * heads * head_dim,
        output_bf16_write_bytes=output_rows * heads * head_dim * 2,
    )


def _repair_rows(
    rows: tuple[int, ...],
    *,
    queries: np.ndarray[Any, Any],
    kv: np.ndarray[Any, Any],
    sinks: np.ndarray[Any, Any],
    indices: np.ndarray[Any, np.dtype[np.int64]],
    scale_binary32: int,
    outputs: np.ndarray[Any, np.dtype[np.uint16]],
    final_max: np.ndarray[Any, np.dtype[np.float32]],
    final_sink_exp: np.ndarray[Any, np.dtype[np.float32]],
    final_denominator: np.ndarray[Any, np.dtype[np.float32]],
    saturated_rows: np.ndarray[Any, np.dtype[np.int64]],
) -> None:
    """Re-execute whole query rows through the exact reference.

    Query rows are independent transactions -- the reference resets the running
    maximum, the denominator and the accumulator at every position -- so one row
    computed alone is the same row computed in company.  A row referred here is
    one the fast schedule could not prove equivalent, and the reference's own
    poison is the poison the caller sees.
    """

    kv_list = kv.tolist()
    sink_list = [int(code) for code in np.asarray(sinks).reshape(-1)]
    for row in rows:
        exact = sparse_attention_bf16(
            [[queries[row].tolist()]],
            [kv_list],
            sink_list,
            [[indices[row].tolist()]],
            scale_binary32=scale_binary32,
        )
        outputs[row] = np.asarray(exact.values[0][0], dtype=np.uint16)
        final_max[row] = (
            np.asarray(exact.final_max_binary32_codes[0][0], dtype=np.uint32)
            .view(np.float32)
        )
        final_sink_exp[row] = (
            np.asarray(exact.sink_exp_binary32_codes[0][0], dtype=np.uint32)
            .view(np.float32)
        )
        final_denominator[row] = (
            np.asarray(exact.final_denominator_binary32_codes[0][0], dtype=np.uint32)
            .view(np.float32)
        )
        saturated_rows[row] = exact.output_saturated_element_count


__all__ = [
    "NUMERIC_CONTRACT",
    "SparseAttentionKernelError",
    "SparseAttentionKernelResult",
    "exp_cr32",
    "sparse_attention_bf16_codes",
]
