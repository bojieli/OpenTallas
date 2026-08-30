"""The data-bearing sparse-attention kernel against its exact scalar oracle.

:mod:`runtime.tensor_accelerator.sparse_attention` schedules the frozen
DeepSeek-V4-Flash contract differently from
:mod:`runtime.reference.sparse_attention`; it must not compute anything
differently.  Every assertion here is on raw encodings, because "close enough"
is not a property this contract has.
"""

from __future__ import annotations

import numpy as np
import pytest

from runtime.reference.formats import binary32_product_add, decode_bf16
from runtime.reference.sparse_attention import (
    SPARSE_ATTENTION_BLOCK_SIZE,
    SPARSE_ATTENTION_SCALE_BINARY32,
    SparseAttentionReferenceError,
    sparse_attention_bf16,
)
from runtime.reference.transcendental import (
    TranscendentalReferenceError,
    binary32_exp_general_rne,
)
from runtime.tensor_accelerator import sparse_attention as kernel


def _bf16(sign: int, binade: int, mantissa: int) -> int:
    """One finite BF16 encoding: 1 sign bit, 8 exponent bits, 7 mantissa bits."""
    return (sign << 15) | ((127 + binade) << 7) | mantissa


def _narrow(values: np.ndarray) -> np.ndarray:
    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    return (upper + increment.astype(np.uint32)).astype(np.uint16)


def _sinks(rng: np.random.Generator, heads: int) -> np.ndarray:
    """Sink logits in the band the real checkpoint audit measured, +-2.5."""
    return np.ascontiguousarray(
        rng.uniform(-2.5, 2.5, heads).astype(np.float32)
    ).view(np.uint32)


def _oracle(query, kv, sinks, indices, scale=SPARSE_ATTENTION_SCALE_BINARY32):
    return sparse_attention_bf16(
        [np.asarray(query).tolist()],
        [np.asarray(kv).tolist()],
        [int(code) for code in np.asarray(sinks).reshape(-1)],
        [np.asarray(indices).tolist()],
        scale_binary32=scale,
    )


def _assert_identical(observed, expected, context: object) -> None:
    assert np.array_equal(
        observed.values, np.asarray(expected.values[0], dtype=np.uint16)
    ), context
    for name in (
        "final_max_binary32_codes",
        "sink_exp_binary32_codes",
        "final_denominator_binary32_codes",
    ):
        assert np.array_equal(
            getattr(observed, name),
            np.asarray(getattr(expected, name)[0], dtype=np.uint32),
        ), (name, context)
    assert (
        observed.output_saturated_element_count
        == expected.output_saturated_element_count
    ), context
    assert observed.counters == expected.counters, context


# ---------------------------------------------------------------------------
# the contract itself
# ---------------------------------------------------------------------------
CASES = [
    # span, heads, head_dim, kv_rows, slots, index pattern
    (1, 1, 4, 4, 1, "full"),
    (2, 2, 4, 6, 8, "full"),
    (1, 2, 6, 8, 63, "full"),
    (1, 2, 6, 8, 64, "full"),
    (3, 2, 6, 9, 70, "full"),
    (2, 1, 5, 12, 129, "full"),
    (3, 2, 6, 9, 70, "causal"),
    (2, 3, 4, 12, 64, "duplicates"),
    (2, 2, 5, 10, 70, "holes"),
    (2, 2, 5, 10, 70, "descending"),
    (4, 1, 8, 20, 65, "one"),
    # More than 64 selected rows: the second source block is the only place the
    # online rescale, the running maximum and the carried denominator do
    # anything at all, and a case that fits one block cannot see them.
    (2, 2, 4, 70, 129, "full"),
    (1, 2, 4, 100, 129, "full"),
    (2, 1, 4, 80, 200, "duplicates"),
]


def _indices(rng, span, slots, rows, pattern):
    """Selected rows in the reference's ``-1``-padded signed form.

    ``holes`` and ``descending`` are legal for the reference and illegal for
    amendment A6, which the engine enforces above the kernel.  The kernel must
    not quietly assume the narrower convention.
    """
    indices = np.full((span, slots), -1, dtype=np.int64)
    for position in range(span):
        if pattern == "full":
            width = min(slots, rows)
            picked = np.sort(rng.choice(rows, size=width, replace=False))
        elif pattern == "causal":
            width = min(position + 1, slots, rows)
            picked = np.arange(width)
        elif pattern == "duplicates":
            width = min(slots, max(2, rows // 2))
            picked = np.sort(rng.integers(0, rows, size=width))
        elif pattern == "one":
            picked = np.array([int(rng.integers(0, rows))])
        elif pattern == "holes":
            keep = rng.random(slots) < 0.5
            keep[0] = True
            indices[position, keep] = np.sort(
                rng.integers(0, rows, size=int(keep.sum()))
            )
            continue
        elif pattern == "descending":
            width = min(slots, rows)
            picked = np.sort(rng.choice(rows, size=width, replace=False))[::-1]
        else:  # pragma: no cover - test data invariant
            raise AssertionError(pattern)
        indices[position, : picked.size] = picked
    return indices


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case[5]}{case[:5]}")
def test_kernel_reproduces_the_scalar_oracle_bit_for_bit(case) -> None:
    span, heads, head_dim, rows, slots, pattern = case
    rng = np.random.default_rng(0x5350415253 + slots * 31 + heads)
    # Operands spanning several binades: a one-binade operand set sums the same
    # in any order and would let a reordered reduction pass unnoticed.
    query = _narrow(
        (
            rng.uniform(-2.0, 2.0, (span, heads, head_dim))
            * 2.0 ** rng.integers(-6, 7, (span, heads, head_dim))
        ).astype(np.float32)
    )
    kv = _narrow(
        (
            rng.uniform(-2.0, 2.0, (rows, head_dim))
            * 2.0 ** rng.integers(-6, 7, (rows, head_dim))
        ).astype(np.float32)
    )
    sinks = _sinks(rng, heads)
    indices = _indices(rng, span, slots, rows, pattern)

    expected = _oracle(query, kv, sinks, indices)
    observed = kernel.sparse_attention_bf16_codes(
        query, kv, sinks, indices, scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32
    )
    _assert_identical(observed, expected, case)
    assert observed.oracle_rows == ()


def test_query_row_tile_length_cannot_change_a_bit(monkeypatch) -> None:
    """The row tile partitions query rows, and that is all it partitions.

    Every query row of a sparse-attention transaction resets the running
    maximum, the denominator and the output accumulator, so a row is an
    independent transaction and no tile length can reach any element's
    reduction.  Tiling one row at a time -- the shape the exact reference
    executes -- must therefore reproduce the batched answer bit for bit, and
    report the same counters.
    """
    rng = np.random.default_rng(0x7113)
    span, heads, head_dim, rows, slots = 7, 2, 6, 12, 70
    query = _narrow(
        (
            rng.uniform(-2.0, 2.0, (span, heads, head_dim))
            * 2.0 ** rng.integers(-6, 7, (span, heads, head_dim))
        ).astype(np.float32)
    )
    kv = _narrow(
        (
            rng.uniform(-2.0, 2.0, (rows, head_dim))
            * 2.0 ** rng.integers(-6, 7, (rows, head_dim))
        ).astype(np.float32)
    )
    sinks = _sinks(rng, heads)
    indices = _indices(rng, span, slots, rows, "full")

    expected = _oracle(query, kv, sinks, indices)
    seen = 0
    for budget in (1, 2, 8, 64, 1 << 10, 1 << 18):
        monkeypatch.setattr(kernel, "_ROW_TILE_ELEMENTS", budget)
        observed = kernel.sparse_attention_bf16_codes(
            query, kv, sinks, indices,
            scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
        )
        _assert_identical(observed, expected, budget)
        seen += 1
    assert seen == 6


def test_underflowing_products_keep_the_contract_single_rounding() -> None:
    """A BF16 product below the smallest normal binary32 rounds; the sum does not.

    The contract's product-add forms the *exact* product and rounds once.  Two
    NumPy ufuncs round twice, and the two disagree exactly when the product
    underflows into a near-zero accumulator.  These operands put every product
    there: subnormal and near-subnormal BF16 magnitudes whose pairwise products
    fall below ``2**-126`` while the accumulator stays small enough to see the
    difference.
    """
    pool = [
        _bf16(0, -125, 0), _bf16(1, -125, 3), _bf16(0, -120, 17),
        _bf16(0, -110, 64), _bf16(1, -100, 5), 0x0001, 0x8001, 0x0040,
        0x0080, 0x8080, 0x0000, _bf16(0, -60, 0), _bf16(1, -70, 9),
    ]
    values = np.asarray(pool, dtype=np.uint16)
    rng = np.random.default_rng(0xDEEF)
    span, heads, head_dim, rows, slots = 2, 2, 8, 9, 70
    query = values[rng.integers(0, values.size, (span, heads, head_dim))]
    kv = values[rng.integers(0, values.size, (rows, head_dim))]
    sinks = _sinks(rng, heads)
    indices = _indices(rng, span, slots, rows, "full")

    expected = _oracle(query, kv, sinks, indices)
    observed = kernel.sparse_attention_bf16_codes(
        query, kv, sinks, indices, scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32
    )
    _assert_identical(observed, expected, "underflowing operands")


def test_signed_zero_and_the_finite_endpoints_match_the_oracle() -> None:
    """Signed zeros the contract canonicalizes, and products that overflow it.

    A product of two BF16 magnitudes near the format's finite endpoint exceeds
    the largest finite binary32 and rounds to infinity, while the exact sum it
    belongs to may still be finite; the exact product the contract forms is what
    decides, not the rounded one.
    """
    pool = [
        0x0000, 0x8000, 0x3F80, 0xBF80, 0x7F7F, 0xFF7F,
        _bf16(0, 120, 0), _bf16(1, 120, 64), _bf16(0, 100, 3), _bf16(1, 60, 0),
    ]
    values = np.asarray(pool, dtype=np.uint16)
    rng = np.random.default_rng(0x0E7)
    span, heads, head_dim, rows, slots = 2, 2, 6, 8, 64
    query = values[rng.integers(0, values.size, (span, heads, head_dim))]
    kv = values[rng.integers(0, values.size, (rows, head_dim))]
    sinks = _sinks(rng, heads)
    indices = _indices(rng, span, slots, rows, "full")

    try:
        expected = _oracle(query, kv, sinks, indices)
    except SparseAttentionReferenceError as exc:
        with pytest.raises(SparseAttentionReferenceError, match=str(exc)[:40]):
            kernel.sparse_attention_bf16_codes(
                query, kv, sinks, indices,
                scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
            )
        return
    observed = kernel.sparse_attention_bf16_codes(
        query, kv, sinks, indices, scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32
    )
    _assert_identical(observed, expected, "endpoint operands")


def test_value_accumulation_visits_its_lanes_in_ascending_slot_order() -> None:
    """Cancellation makes the AV order observable, and it is ascending.

    The query is nonzero in channel 0 only and every selected KV row carries the
    same channel-0 value, so every score -- and therefore every probability --
    is identical.  Channel 1 then holds ``+2**20``, ``-2**20`` and four copies
    of ``2**-8``.  Accumulated in ascending slot order the pair annihilates
    first and the four small terms survive; in any order that puts them last
    they are below half an ulp of ``2**20`` and vanish.  A benign operand set
    would sum the same either way and let a reordered lane loop pass.
    """
    span, heads, head_dim, rows, slots = 1, 1, 4, 6, 8
    query = np.zeros((span, heads, head_dim), dtype=np.uint16)
    query[0, 0, 0] = 0x3F80                       # 1.0
    kv = np.zeros((rows, head_dim), dtype=np.uint16)
    kv[:, 0] = 0x3F80                             # every score identical
    kv[0, 1] = _bf16(0, 20, 0)                    # +2**20
    kv[1, 1] = _bf16(1, 20, 0)                    # -2**20
    kv[2:, 1] = _bf16(0, -8, 0)                   # 2**-8, four times
    sinks = np.ascontiguousarray(np.zeros(heads, dtype=np.float32)).view(np.uint32)
    indices = np.full((span, slots), -1, dtype=np.int64)
    indices[0, :rows] = np.arange(rows)

    expected = _oracle(query, kv, sinks, indices)
    observed = kernel.sparse_attention_bf16_codes(
        query, kv, sinks, indices, scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32
    )
    _assert_identical(observed, expected, "cancelling lanes")
    # The four surviving terms are what a reordered lane loop would lose.
    assert observed.values[0, 0, 1] != 0


def test_the_underflow_repair_runs_on_operands_that_need_it(monkeypatch) -> None:
    """The detector has to fire, in both contractions, or it pins nothing.

    ``_rounds_twice`` is asked about an accumulator shaped ``[rows, heads, k]``:
    ``k`` is the source-block lane count in the QK contraction and the head
    dimension in the AV one, which is how this tells the two apart.  The
    operands are the subnormal pool, where BF16 products underflow binary32
    into near-zero accumulators in both.
    """
    pool = [
        _bf16(0, -125, 0), _bf16(1, -125, 3), _bf16(0, -120, 17),
        _bf16(0, -110, 64), _bf16(1, -100, 5), 0x0001, 0x8001, 0x0040,
        0x0080, 0x8080, 0x0000, _bf16(0, -60, 0), _bf16(1, -70, 9),
    ]
    values = np.asarray(pool, dtype=np.uint16)
    rng = np.random.default_rng(0xDEEF + 10)
    span, heads, head_dim, rows, slots = 2, 2, 8, 9, 70
    query = values[rng.integers(0, values.size, (span, heads, head_dim))]
    kv = values[rng.integers(0, values.size, (rows, head_dim))]
    sinks = _sinks(rng, heads)
    indices = _indices(rng, span, slots, rows, "full")

    repaired: dict[int, int] = {}
    original = kernel._rounds_twice

    def watched(accumulator, product):
        risky = original(accumulator, product)
        if risky is not None:
            width = int(accumulator.shape[-1])
            repaired[width] = repaired.get(width, 0) + int(risky.sum())
        return risky

    monkeypatch.setattr(kernel, "_rounds_twice", watched)
    observed = kernel.sparse_attention_bf16_codes(
        query, kv, sinks, indices, scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32
    )
    monkeypatch.undo()
    expected = _oracle(query, kv, sinks, indices)
    _assert_identical(observed, expected, "subnormal pool")
    assert repaired.get(head_dim, 0) > 0, ("no AV product-add was repaired", repaired)
    assert repaired.get(SPARSE_ATTENTION_BLOCK_SIZE, 0) > 0, (
        "no QK product-add was repaired",
        repaired,
    )


def test_the_exact_product_add_is_not_two_roundings() -> None:
    """One rounding of ``a + b*c`` is not two roundings, and this is the case.

    ``a`` is the smallest positive binary32 subnormal and ``b*c`` is exactly
    one and a half of them.  The exact sum is two and a half units and rounds
    to two, ties to even.  Rounding the product first turns it into two units
    -- also ties to even -- and the sum then lands on three.  This is the whole
    reason the kernel carries :func:`_single_rounded_add`, and the reason its
    cheap per-row bound has to be conservative rather than clever.
    """
    accumulator = np.array([0x00000001], dtype=np.uint32).view(np.float32)
    left = (np.array([0x35C0], dtype=np.uint32) << np.uint32(16)).view(np.float32)
    right = (np.array([0x0010], dtype=np.uint32) << np.uint32(16)).view(np.float32)
    expected = binary32_product_add(
        0x00000001, decode_bf16(0x35C0).value, decode_bf16(0x0010).value
    )
    with np.errstate(under="ignore"):
        naive = accumulator + left * right
        observed = kernel._single_rounded_add(accumulator, left, right)
    assert int(np.ascontiguousarray(naive).view(np.uint32)[0]) != expected
    assert int(np.ascontiguousarray(observed).view(np.uint32)[0]) == expected
    # And the detector has to be able to see it: the product underflows below
    # the smallest normal binary32 into a nonzero, negligible accumulator.
    risky = kernel._rounds_twice(accumulator, left * right)
    assert risky is not None and bool(risky[0])


# ---------------------------------------------------------------------------
# the exponential
# ---------------------------------------------------------------------------
def test_exponential_is_the_correctly_rounded_binary32_one() -> None:
    """``exp_cr32`` answers to the exact rational enclosure, not to ``libm``.

    The candidate comes from the host's binary64 exponential and is only
    accepted when perturbing it by ``2**-40`` relative cannot change the
    binary32 it rounds to; anything else is referred to the exact reference.
    The sampled domain covers the score offsets the contract actually forms
    (nonpositive), the sink offset (either sign), gradual underflow to zero at
    about -104, and the positive overflow edge near +88.72.
    """
    rng = np.random.default_rng(0x4558)
    sampled = [
        np.float32(0.0), np.float32(-0.0),
        np.float32(-103.9), np.float32(-104.1), np.float32(-88.0),
        np.float32(88.7), np.float32(88.73), np.float32(-255.9),
    ]
    # Inputs the proof rejects: an exhaustive scan of the score-offset domain
    # found 7,811 of 1,120,927,745, all of them where the binary64 exponential
    # lands within 2**-40 of a binary32 rounding boundary.  These reach the
    # exact-reference branch, which is the branch that owes nothing to libm.
    sampled.extend(
        np.array(
            [0xB2FFFE01, 0xB2FFFE02, 0xB2FFFE03, 0xB3000000, 0xB3000002],
            dtype=np.uint32,
        ).view(np.float32)
    )
    for span in (1e-6, 1.0, 20.0, 90.0, 200.0):
        sampled.extend(-np.abs(rng.uniform(0, span, 300)).astype(np.float32))
    sampled.extend(rng.uniform(-90.0, 88.5, 400).astype(np.float32))
    values = np.ascontiguousarray(np.asarray(sampled, dtype=np.float32))

    observed = kernel.exp_cr32(values)
    observed_codes = np.ascontiguousarray(observed).view(np.uint32)
    input_codes = values.view(np.uint32)
    compared = 0
    for index in range(values.size):
        try:
            expected = binary32_exp_general_rne(int(input_codes[index]))
        except TranscendentalReferenceError:
            assert not np.isfinite(observed[index]), float(values[index])
            compared += 1
            continue
        assert int(observed_codes[index]) == expected, (
            float(values[index]),
            hex(int(observed_codes[index])),
            hex(expected),
        )
        compared += 1
    assert compared == values.size and compared > 1000


# ---------------------------------------------------------------------------
# poison
# ---------------------------------------------------------------------------
def test_poison_raises_with_the_reference_message() -> None:
    """A sink far above the running maximum overflows the exponential.

    The kernel does not decide that; it detects that its schedule produced a
    nonfinite intermediate and re-executes the query row through the reference,
    so the transaction is poisoned by the reference, with the reference's own
    message.
    """
    rng = np.random.default_rng(0xDEAD)
    query = _narrow(rng.uniform(-1.0, 1.0, (1, 1, 4)).astype(np.float32))
    kv = _narrow(rng.uniform(-1.0, 1.0, (4, 4)).astype(np.float32))
    sinks = np.ascontiguousarray(np.asarray([1.0e30], dtype=np.float32)).view(
        np.uint32
    )
    indices = np.asarray([[0, 1, 2, 3]], dtype=np.int64)

    with pytest.raises(SparseAttentionReferenceError) as reference:
        _oracle(query, kv, sinks, indices)
    with pytest.raises(SparseAttentionReferenceError) as observed:
        kernel.sparse_attention_bf16_codes(
            query, kv, sinks, indices,
            scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
        )
    assert str(observed.value) == str(reference.value)


def test_an_all_padding_first_source_block_is_refused() -> None:
    """The contract starts its maximum at negative infinity, which needs a row."""
    query = np.full((1, 1, 4), 0x3F80, dtype=np.uint16)
    kv = np.full((4, 4), 0x3F80, dtype=np.uint16)
    sinks = np.ascontiguousarray(np.zeros(1, dtype=np.float32)).view(np.uint32)
    indices = np.full((1, SPARSE_ATTENTION_BLOCK_SIZE + 2), -1, dtype=np.int64)
    indices[0, SPARSE_ATTENTION_BLOCK_SIZE] = 1
    with pytest.raises(SparseAttentionReferenceError, match="first 64-slot"):
        kernel.sparse_attention_bf16_codes(
            query, kv, sinks, indices,
            scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
        )
