from __future__ import annotations

import inspect
from fractions import Fraction

import pytest

from runtime.service_engine import hc_pre_numeric
from runtime.service_engine.hc_pre_numeric import (
    HC_PRE_FLATTENED_WIDTH,
    HC_PRE_HC_MULT,
    HC_PRE_MIX_FIELDS,
    HC_PRE_NORM_EPSILON_BINARY32,
    HC_PRE_SINKHORN_EPSILON_BINARY32,
    HC_PRE_SINKHORN_ITERATIONS,
    HC_PRE_WIDTH,
    HCPreServiceNumericError,
    HCPreServiceResult,
    cr32_exp,
    cr32_rsqrt,
    cr32_sigmoid,
    execute_hc_pre,
    hc_pre_branch_column,
    rn32_add,
    rn32_affine,
    rn32_balanced_sum4,
    rn32_fused_product_add,
    rn32_multiply,
    sinkhorn20,
)


_ZERO_STREAM = (0,) * HC_PRE_WIDTH
_ZERO_TOKEN = (_ZERO_STREAM,) * HC_PRE_HC_MULT
_ZERO_PROJECTION_ROW = (0,) * HC_PRE_FLATTENED_WIDTH
_ZERO_PROJECTION = (_ZERO_PROJECTION_ROW,) * HC_PRE_MIX_FIELDS
_ZERO_SCALES = (0,) * 3
_ZERO_BASES = (0,) * HC_PRE_MIX_FIELDS


def _zero_x(batch: int, sequence: int) -> tuple[tuple[object, ...], ...]:
    return tuple(tuple(_ZERO_TOKEN for _ in range(sequence)) for _ in range(batch))


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent)
    return Fraction(1, 1 << -exponent)


def _oracle_decode(code: int) -> Fraction:
    sign = -1 if code & 0x80000000 else 1
    exponent = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent == 0:
        return Fraction(sign * fraction) * _pow2(-149)
    return Fraction(sign * ((1 << 23) | fraction)) * _pow2(exponent - 150)


def _oracle_round_integer(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    if remainder * 2 > value.denominator or (
        remainder * 2 == value.denominator and quotient & 1
    ):
        quotient += 1
    return quotient


def _oracle_encode(value: Fraction) -> int:
    """Small independent exact-rational binary32 encoder for Sinkhorn tests."""

    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    if magnitude < _pow2(-126):
        significand = _oracle_round_integer(magnitude / _pow2(-149))
        return 0 if significand == 0 else sign | significand
    exponent = magnitude.numerator.bit_length() - magnitude.denominator.bit_length()
    if magnitude < _pow2(exponent):
        exponent -= 1
    significand = _oracle_round_integer(magnitude / _pow2(exponent - 23))
    if significand == 1 << 24:
        significand >>= 1
        exponent += 1
    if exponent > 127:
        raise OverflowError
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def _oracle_add(left: int, right: int) -> int:
    return _oracle_encode(_oracle_decode(left) + _oracle_decode(right))


def _oracle_divide(numerator: int, denominator: int) -> int:
    return _oracle_encode(_oracle_decode(numerator) / _oracle_decode(denominator))


def _oracle_sum4(row: tuple[int, int, int, int]) -> int:
    return _oracle_add(
        _oracle_add(row[0], row[1]),
        _oracle_add(row[2], row[3]),
    )


def _transpose(matrix: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(matrix[source][destination] for source in range(4))
        for destination in range(4)
    )


def _oracle_sinkhorn(
    comb_z: tuple[tuple[int, int, int, int], ...],
    stages: int,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    epsilon = HC_PRE_SINKHORN_EPSILON_BINARY32
    stable_rows: list[tuple[int, ...]] = []
    for row in comb_z:
        maximum = max(row, key=_oracle_decode)
        deltas = tuple(
            _oracle_add(code, 0 if maximum == 0 else maximum ^ 0x80000000)
            for code in row
        )
        # This oracle's deliberately chosen inputs make every required exp
        # either exp(0) -> 1 or exp(x <= -150) -> correctly rounded +0.
        exponentials = tuple(0x3F800000 if delta == 0 else 0 for delta in deltas)
        row_sum = _oracle_sum4(exponentials)  # type: ignore[arg-type]
        stable_rows.append(
            tuple(
                _oracle_add(_oracle_divide(code, row_sum), epsilon)
                for code in exponentials
            )
        )
    stable = tuple(stable_rows)
    result = stable

    def column_stage(
        matrix: tuple[tuple[int, ...], ...],
    ) -> tuple[tuple[int, ...], ...]:
        denominators = tuple(
            _oracle_add(
                _oracle_sum4(
                    tuple(matrix[source][destination] for source in range(4))  # type: ignore[arg-type]
                ),
                epsilon,
            )
            for destination in range(4)
        )
        return tuple(
            tuple(
                _oracle_divide(row[destination], denominators[destination])
                for destination in range(4)
            )
            for row in matrix
        )

    result = column_stage(result)
    for _ in range(stages - 1):
        row_denominators = tuple(
            _oracle_add(_oracle_sum4(row), epsilon)  # type: ignore[arg-type]
            for row in result
        )
        result = tuple(
            tuple(_oracle_divide(code, denominator) for code in row)
            for row, denominator in zip(result, row_denominators, strict=True)
        )
        result = column_stage(result)
    return stable, result


def test_service_hc_pre_contract_is_pinned_and_lane_independent() -> None:
    assert HC_PRE_HC_MULT == 4
    assert HC_PRE_WIDTH == 4096
    assert HC_PRE_FLATTENED_WIDTH == 16384
    assert HC_PRE_MIX_FIELDS == 24
    assert HC_PRE_SINKHORN_ITERATIONS == 20
    assert HC_PRE_NORM_EPSILON_BINARY32 == 0x358637BD
    assert HC_PRE_SINKHORN_EPSILON_BINARY32 == 0x358637BD

    source = inspect.getsource(hc_pre_numeric)
    assert "runtime.reference" not in source
    assert "rms_numeric" not in source
    assert "import math" not in source
    assert "numpy" not in source
    assert hc_pre_numeric._cr32_exp_validated.cache_info().maxsize == 4096
    assert hc_pre_numeric._cr32_sigmoid_validated.cache_info().maxsize == 4096


@pytest.mark.parametrize(
    ("input_code", "exp_code", "sigmoid_code"),
    [
        (0xC315FFFF, 0x00000000, 0x00000000),
        (0xC2C80000, 0x0000001B, 0x0000001B),
        (0xC1A00000, 0x310DA433, 0x310DA433),
        (0xC0000000, 0x3E0A9555, 0x3DF420A9),
        (0xBF800000, 0x3EBC5AB2, 0x3E89B2B1),
        (0xBF000000, 0x3F1B4598, 0x3EC14D03),
        (0x80800000, 0x3F800000, 0x3F000000),
        (0x80000001, 0x3F800000, 0x3F000000),
        (0x00000000, 0x3F800000, 0x3F000000),
        (0x00000001, 0x3F800000, 0x3F000000),
        (0x00800000, 0x3F800000, 0x3F000000),
        (0x3F000000, 0x3FD3094C, 0x3F1F597F),
        (0x3F800000, 0x402DF854, 0x3F3B26A8),
        (0x40000000, 0x40EC7326, 0x3F617BEB),
        (0x41200000, 0x46AC14EE, 0x3F7FFD06),
        (0x41A00000, 0x4DE75844, 0x3F800000),
        (0x42A00000, 0x792ABBCE, 0x3F800000),
    ],
)
def test_cr32_transcendentals_match_independent_directed_mpfr_corpus(
    input_code: int,
    exp_code: int,
    sigmoid_code: int,
) -> None:
    # These frozen codes were generated independently with 1,024-bit MPFR.
    # Each lower/upper directed MPFR enclosure rounded to the same binary32
    # code; the production Decimal interval implementation was not involved.
    assert cr32_exp(input_code) == exp_code
    assert cr32_sigmoid(input_code) == sigmoid_code


def test_cr32_transcendental_extremes_and_exceptions_are_exact() -> None:
    assert cr32_exp(0xC3160000) == 0  # exp(-150) < 2^-150
    assert cr32_sigmoid(0xC3160000) == 0
    assert cr32_sigmoid(0x41C80000) == 0x3F800000  # z=25
    assert cr32_rsqrt(HC_PRE_NORM_EPSILON_BINARY32) == 0x447A0000
    assert cr32_rsqrt(0x3F800000) == 0x3F800000

    with pytest.raises(HCPreServiceNumericError, match="nonfinite binary32"):
        cr32_exp(0x43000000)
    with pytest.raises(HCPreServiceNumericError, match="finite binary32"):
        cr32_sigmoid(0x7F800000)
    with pytest.raises(HCPreServiceNumericError, match="must be positive"):
        cr32_rsqrt(0)


def test_cr32_certificate_refines_without_a_fixed_precision_cap() -> None:
    requested_precisions: list[int] = []

    def delayed_certificate(precision: int) -> tuple[Fraction, Fraction]:
        requested_precisions.append(precision)
        if precision < 768:
            return Fraction(1), Fraction(1) + _pow2(-23)
        return Fraction(1), Fraction(1)

    assert hc_pre_numeric._certify_interval_binary32(delayed_certificate) == 0x3F800000
    assert requested_precisions == [192, 384, 768]


def test_projection_fma_and_affine_round_at_the_declared_boundaries() -> None:
    accumulator = rn32_fused_product_add(0, 0x3F800000, 0x3F800000)
    accumulator = rn32_fused_product_add(accumulator, 0x39800000, 0x39800000)
    accumulator = rn32_fused_product_add(accumulator, 0xBF800000, 0x3F800000)
    assert accumulator == 0

    # An exact one-round dot product would retain 2^-24 (0x33800000).
    exact_dot = Fraction(1) + _pow2(-24) - 1
    assert _oracle_encode(exact_dot) == 0x33800000

    value = 0xC22E9A02
    scale = 0x40BC9F5E
    base = 0xC298A0B6
    assert rn32_affine(value, scale, base) == 0xC3A6CDF8
    assert rn32_fused_product_add(base, value, scale) == 0xC3A6CDF9


def test_four_source_branch_uses_balanced_order_through_bf16_conversion() -> None:
    values = (0x321C0000, 0xC93A0000, 0xC96B0000, 0xBDAF0000)
    assert rn32_balanced_sum4(values) == 0xC9D28000

    left_fold = 0
    for value in values:
        left_fold = rn32_add(left_fold, value)
    assert left_fold == 0xC9D28001

    branch_code, saturated = hc_pre_branch_column(
        (0x3F800000,) * 4,
        (0x321C, 0xC93A, 0xC96B, 0xBDAF),
    )
    assert branch_code == 0xC9D2
    # The left-associated code converts to adjacent BF16 0xc9d3.
    assert not saturated


def test_scalar_rn32_preserves_subnormals_and_poisons_exceptions() -> None:
    assert rn32_add(0x80000000, 0) == 0
    assert rn32_multiply(0x00000001, 0x3F800000) == 0x00000001
    assert rn32_multiply(0x80000001, 0x3F000000) == 0

    with pytest.raises(HCPreServiceNumericError, match="arithmetic overflow"):
        rn32_multiply(0x7F7FFFFF, 0x40000000)
    with pytest.raises(HCPreServiceNumericError, match="finite binary32"):
        rn32_add(0x7FC00000, 0)
    with pytest.raises(HCPreServiceNumericError, match="unsigned 32-bit"):
        rn32_add(True, 0)


def test_sinkhorn_has_exactly_twenty_pairs_and_source_destination_orientation() -> None:
    zero = 0
    negative_150 = 0xC3160000
    asymmetric = (
        (zero, negative_150, negative_150, negative_150),
        (zero, zero, negative_150, negative_150),
        (negative_150, zero, zero, negative_150),
        (negative_150, negative_150, zero, zero),
    )

    stable, actual = sinkhorn20(asymmetric)
    expected_stable, expected_20 = _oracle_sinkhorn(asymmetric, 20)
    _, expected_19 = _oracle_sinkhorn(asymmetric, 19)
    transposed_input = _transpose(asymmetric)
    _, transposed_result = _oracle_sinkhorn(transposed_input, 20)  # type: ignore[arg-type]
    wrong_orientation = _transpose(transposed_result)

    assert stable == expected_stable
    assert actual == expected_20
    assert actual != expected_19
    assert actual != wrong_orientation
    assert stable[0] == (
        0x3F800008,
        HC_PRE_SINKHORN_EPSILON_BINARY32,
        HC_PRE_SINKHORN_EPSILON_BINARY32,
        HC_PRE_SINKHORN_EPSILON_BINARY32,
    )


def test_all_zero_anchor_and_exact_semantic_counters() -> None:
    x = _zero_x(1, 1)
    result = execute_hc_pre(
        x,
        _ZERO_PROJECTION,
        _ZERO_SCALES,
        _ZERO_BASES,
    )

    assert isinstance(result, HCPreServiceResult)
    assert result.rms_mean_codes == ((0,),)
    assert result.rms_inverse_codes == ((0x447A0000,),)
    assert result.projection_codes == (((0,) * 24,),)
    assert result.mix_codes == (((0,) * 24,),)
    assert result.pre_codes == (((0x3F000011,) * 4,),)
    assert result.post_codes == (((0x3F800000,) * 4,),)
    assert result.stable_softmax_codes == ((((0x3E800022,) * 4,) * 4,),)
    assert result.combination_codes == ((((0x3E7FFFF0,) * 4,) * 4,),)
    assert result.branch_codes == (((0,) * HC_PRE_WIDTH,),)
    assert result.residual_codes == x
    assert result.branch_saturation_count == 0
    assert dict(result.logical_counters) == {
        "hc_pre_input_bf16_values": 16_384,
        "hc_pre_rms_square_multiplies": 16_384,
        "hc_pre_rms_reduction_adds": 16_383,
        "hc_pre_rms_divides": 1,
        "hc_pre_rms_epsilon_adds": 1,
        "hc_pre_rsqrt_evaluations": 1,
        "hc_pre_projection_product_accumulates": 393_216,
        "hc_pre_projection_rms_multiplies": 24,
        "hc_pre_field_affine_multiplies": 24,
        "hc_pre_field_affine_adds": 24,
        "hc_pre_sigmoid_evaluations": 8,
        "hc_pre_coefficient_epsilon_adds": 4,
        "hc_pre_post_factor_multiplies": 4,
        "hc_pre_softmax_max_comparisons": 12,
        "hc_pre_softmax_subtracts": 16,
        "hc_pre_exp_evaluations": 16,
        "hc_pre_sinkhorn_row_stages": 20,
        "hc_pre_sinkhorn_column_stages": 20,
        "hc_pre_sinkhorn_row_reduction_adds": 240,
        "hc_pre_sinkhorn_column_reduction_adds": 240,
        "hc_pre_sinkhorn_divides": 640,
        "hc_pre_sinkhorn_epsilon_adds": 172,
        "hc_pre_branch_coefficient_multiplies": 16_384,
        "hc_pre_branch_reduction_adds": 12_288,
        "hc_pre_branch_bf16_conversions": 4_096,
        "hc_pre_residual_bf16_values_preserved": 16_384,
        "hc_pre_branch_bf16_saturations": 0,
    }
    with pytest.raises(TypeError):
        result.logical_counters["hc_pre_rms_divides"] = 2  # type: ignore[index]


@pytest.mark.parametrize(("batch", "sequence"), [(1, 1), (1, 2), (3, 1), (2, 2)])
def test_hc_pre_accepts_every_qualified_token_extent(
    batch: int,
    sequence: int,
) -> None:
    token_count = batch * sequence
    result = execute_hc_pre(
        _zero_x(batch, sequence),
        _ZERO_PROJECTION,
        _ZERO_SCALES,
        _ZERO_BASES,
    )

    assert len(result.branch_codes) == batch
    assert all(len(rows) == sequence for rows in result.branch_codes)
    assert all(len(row) == HC_PRE_WIDTH for rows in result.branch_codes for row in rows)
    assert result.logical_counters["hc_pre_projection_product_accumulates"] == (
        393_216 * token_count
    )
    assert result.logical_counters["hc_pre_sinkhorn_row_stages"] == 20 * token_count
    assert result.logical_counters["hc_pre_sinkhorn_column_stages"] == 20 * token_count


def test_width_16384_rms_uses_the_fourteen_level_balanced_tree() -> None:
    # square(1) is 1 and square(2^-12) is 2^-24.  A left fold loses all
    # 16,383 midpoint contributions and gives mean 0x38800000.  The canonical
    # tree loses only the first tied contribution and retains 8,191 ulps.
    tiny = 0x3980
    token = (
        (0x3F80,) + (tiny,) * (HC_PRE_WIDTH - 1),
        (tiny,) * HC_PRE_WIDTH,
        (tiny,) * HC_PRE_WIDTH,
        (tiny,) * HC_PRE_WIDTH,
    )
    result = execute_hc_pre(
        ((token,),),
        _ZERO_PROJECTION,
        _ZERO_SCALES,
        _ZERO_BASES,
    )

    assert result.rms_mean_codes == ((0x38801FFF,),)
    assert result.rms_mean_codes != ((0x38800000,),)


def test_full_projection_traverses_increasing_k_with_one_round_per_product_add() -> (
    None
):
    stream0 = (
        0x3F80,
        0x3980,
        0xBF80,
    ) + (0,) * (HC_PRE_WIDTH - 3)
    token = (stream0, _ZERO_STREAM, _ZERO_STREAM, _ZERO_STREAM)
    projection0 = (
        0x3F800000,
        0x39800000,
        0x3F800000,
    ) + (0,) * (HC_PRE_FLATTENED_WIDTH - 3)
    projection = (projection0,) + (_ZERO_PROJECTION_ROW,) * 23

    result = execute_hc_pre(
        ((token,),),
        projection,
        _ZERO_SCALES,
        _ZERO_BASES,
    )

    assert result.projection_codes == (((0,) * 24,),)
    # A one-round exact dot would expose 2^-24 instead.
    assert _oracle_encode(Fraction(1) + _pow2(-24) - 1) == 0x33800000


def test_residual_is_bit_preserving_but_arithmetic_zero_is_canonical_positive() -> None:
    negative_zero_stream = (0x8000,) * HC_PRE_WIDTH
    token = (negative_zero_stream,) * HC_PRE_HC_MULT
    x = ((token,),)

    result = execute_hc_pre(
        x,
        _ZERO_PROJECTION,
        _ZERO_SCALES,
        _ZERO_BASES,
    )

    assert result.residual_codes == x
    assert result.rms_mean_codes == ((0,),)
    assert result.projection_codes == (((0,) * 24,),)
    assert result.branch_codes == (((0,) * HC_PRE_WIDTH,),)


@pytest.mark.parametrize(
    ("norm_epsilon", "hc_epsilon", "match"),
    [
        (0x358637BC, HC_PRE_SINKHORN_EPSILON_BINARY32, "norm_epsilon"),
        (HC_PRE_NORM_EPSILON_BINARY32, 0x358637BC, "hc_epsilon"),
        (True, HC_PRE_SINKHORN_EPSILON_BINARY32, "norm_epsilon"),
        (HC_PRE_NORM_EPSILON_BINARY32, 1e-6, "hc_epsilon"),
    ],
)
def test_distinct_profile_epsilon_fields_are_independently_checked(
    norm_epsilon: object,
    hc_epsilon: object,
    match: str,
) -> None:
    with pytest.raises(HCPreServiceNumericError, match=match):
        execute_hc_pre(
            _zero_x(1, 1),
            _ZERO_PROJECTION,
            _ZERO_SCALES,
            _ZERO_BASES,
            norm_epsilon_binary32=norm_epsilon,  # type: ignore[arg-type]
            hc_epsilon_binary32=hc_epsilon,  # type: ignore[arg-type]
        )


def test_malformed_nonfinite_and_overflowing_commands_poison_atomically() -> None:
    with pytest.raises(HCPreServiceNumericError, match="batch extent"):
        execute_hc_pre((), _ZERO_PROJECTION, _ZERO_SCALES, _ZERO_BASES)

    with pytest.raises(HCPreServiceNumericError, match=r"batch\*sequence.*1\.\.4"):
        execute_hc_pre(_zero_x(1, 5), _ZERO_PROJECTION, _ZERO_SCALES, _ZERO_BASES)

    short_token = ((_ZERO_STREAM,) * 3,)
    with pytest.raises(HCPreServiceNumericError, match="exactly 4 HC streams"):
        execute_hc_pre(short_token, _ZERO_PROJECTION, _ZERO_SCALES, _ZERO_BASES)

    bad_stream = (0,) * (HC_PRE_WIDTH - 1) + (0x7F80,)
    bad_second_token = (_ZERO_STREAM, _ZERO_STREAM, _ZERO_STREAM, bad_stream)
    x_with_late_poison = ((_ZERO_TOKEN, bad_second_token),)
    with pytest.raises(
        HCPreServiceNumericError,
        match=r"x_codes\[0\]\[1\]\[3\].*finite BF16",
    ):
        execute_hc_pre(
            x_with_late_poison,
            _ZERO_PROJECTION,
            _ZERO_SCALES,
            _ZERO_BASES,
        )

    bad_projection_row = (0,) * (HC_PRE_FLATTENED_WIDTH - 1) + (0x7F800000,)
    bad_projection = (_ZERO_PROJECTION_ROW,) * 23 + (bad_projection_row,)
    with pytest.raises(HCPreServiceNumericError, match="finite binary32"):
        execute_hc_pre(
            _zero_x(1, 1),
            bad_projection,
            _ZERO_SCALES,
            _ZERO_BASES,
        )

    overflowing_stream = (0x7F7F,) + (0,) * (HC_PRE_WIDTH - 1)
    overflowing_token = (overflowing_stream,) + (_ZERO_STREAM,) * 3
    with pytest.raises(
        HCPreServiceNumericError,
        match=r"token \[0\]\[0\].*arithmetic overflow",
    ):
        execute_hc_pre(
            ((overflowing_token,),),
            _ZERO_PROJECTION,
            _ZERO_SCALES,
            _ZERO_BASES,
        )

    # Row zero can complete internally, but a numeric exception in row one
    # still raises without returning any partial result, diagnostics, or counts.
    with pytest.raises(
        HCPreServiceNumericError,
        match=r"token \[0\]\[1\].*arithmetic overflow",
    ):
        execute_hc_pre(
            ((_ZERO_TOKEN, overflowing_token),),
            _ZERO_PROJECTION,
            _ZERO_SCALES,
            _ZERO_BASES,
        )
