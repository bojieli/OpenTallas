"""Independent artifact-service arithmetic for DeepSeek V4 ``HC_PRE``.

This module implements the fixed NUM-6.10 profile directly from raw BF16 and
binary32 encodings.  It deliberately does not share numeric helpers with the
runtime reference lane (or with the separately qualified RMS service): every
rounding point, tree edge, and exceptional-value check is local to this
artifact-service implementation.

The exponential and logistic boundaries do not call host ``libm``.  They use
the standard library's correctly rounded decimal exponential to construct a
closed rational interval, then refine that interval until both endpoints round
to the same binary32 code.  Thus decimal arithmetic is only a certificate for
the required binary result; it is not a visible approximation boundary.
Refinement has no fixed precision cap.  An exhaustive binary32 campaign is
still required to qualify a finite worst-case work bound; that performance
evidence obligation does not alter the functional termination proof below.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import MAX_EMAX, MIN_EMIN, Decimal, localcontext
from functools import lru_cache
from fractions import Fraction
from types import MappingProxyType
from typing import TypeAlias


HC_PRE_HC_MULT = 4
HC_PRE_WIDTH = 4096
HC_PRE_FLATTENED_WIDTH = HC_PRE_HC_MULT * HC_PRE_WIDTH
HC_PRE_MIX_FIELDS = (2 + HC_PRE_HC_MULT) * HC_PRE_HC_MULT
HC_PRE_SINKHORN_ITERATIONS = 20
HC_PRE_NORM_EPSILON_BINARY32 = 0x358637BD
HC_PRE_SINKHORN_EPSILON_BINARY32 = 0x358637BD

_BINARY32_ONE = 0x3F800000
_BINARY32_TWO = 0x40000000
_BINARY32_WIDTH = 0x46800000  # exact binary32 encoding of 16,384
_BINARY32_MAX_FINITE = 0x7F7FFFFF

BF16Vector: TypeAlias = tuple[int, ...]
BF16HCRow: TypeAlias = tuple[BF16Vector, ...]
BF16Tensor4: TypeAlias = tuple[tuple[BF16HCRow, ...], ...]
BF16Tensor3: TypeAlias = tuple[tuple[BF16Vector, ...], ...]
F32Vector: TypeAlias = tuple[int, ...]
F32Matrix: TypeAlias = tuple[F32Vector, ...]
F32Tensor3: TypeAlias = tuple[tuple[F32Vector, ...], ...]
F32Tensor4: TypeAlias = tuple[tuple[F32Matrix, ...], ...]


class HCPreServiceNumericError(ValueError):
    """Raised when a complete HC_PRE service command must be poisoned."""


@dataclass(frozen=True)
class HCPreServiceResult:
    """Atomic HC_PRE result, diagnostics, and semantic reconciliation counts."""

    branch_codes: BF16Tensor3
    post_codes: F32Tensor3
    combination_codes: F32Tensor4
    residual_codes: BF16Tensor4
    rms_mean_codes: tuple[tuple[int, ...], ...]
    rms_inverse_codes: tuple[tuple[int, ...], ...]
    projection_codes: F32Tensor3
    mix_codes: F32Tensor3
    pre_codes: F32Tensor3
    stable_softmax_codes: F32Tensor4
    branch_saturation_count: int
    logical_counters: Mapping[str, int]

    @property
    def comb_codes(self) -> F32Tensor4:
        """Short architectural alias for ``combination_codes``."""

        return self.combination_codes

    @property
    def semantic_counters(self) -> Mapping[str, int]:
        """Alias emphasizing that the counters are semantic, not physical."""

        return self.logical_counters


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise HCPreServiceNumericError(f"{label} must be a sequence")
    return value


def _validate_unsigned_code(value: object, bits: int, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < 1 << bits
    ):
        raise HCPreServiceNumericError(
            f"{label} must be an unsigned {bits}-bit encoding"
        )
    return value


def _validate_finite_binary32(value: object, label: str) -> int:
    code = _validate_unsigned_code(value, 32, label)
    if code & 0x7F800000 == 0x7F800000:
        raise HCPreServiceNumericError(f"{label} must be finite binary32")
    # All arithmetic boundaries consume canonical positive zero.
    return 0 if code & 0x7FFFFFFF == 0 else code


def _validate_finite_bf16(value: object, label: str) -> int:
    code = _validate_unsigned_code(value, 16, label)
    if code & 0x7F80 == 0x7F80:
        raise HCPreServiceNumericError(f"{label} must be finite BF16")
    return code


def _round_integer_right(value: int, shift: int) -> int:
    """Return RNE(value / 2**shift) for a nonnegative integer value."""

    if shift <= 0:
        return value << -shift
    quotient, remainder = divmod(value, 1 << shift)
    midpoint = 1 << (shift - 1)
    if remainder > midpoint or (remainder == midpoint and quotient & 1):
        quotient += 1
    return quotient


def _decode_binary32_dyadic(code: int) -> tuple[int, int]:
    """Decode finite binary32 as ``integer * 2**exponent``."""

    exponent_field = (code >> 23) & 0xFF
    fraction = code & 0x7FFFFF
    if exponent_field == 0xFF:
        raise HCPreServiceNumericError("binary32 NaN or infinity is not arithmetic")
    if exponent_field == 0:
        significand = fraction
        exponent = -149
    else:
        significand = (1 << 23) | fraction
        exponent = exponent_field - 150
    if code & 0x80000000:
        significand = -significand
    return significand, exponent


def _encode_binary32_dyadic(integer: int, exponent: int) -> int:
    """RNE-encode an exact dyadic value, preserving binary32 subnormals."""

    if integer == 0:
        return 0
    sign = 0x80000000 if integer < 0 else 0
    magnitude = abs(integer)
    exact_exponent = magnitude.bit_length() - 1 + exponent

    if exact_exponent < -126:
        significand = _round_integer_right(magnitude, -(exponent + 149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        # Rounding the largest subnormal interval can produce min-normal.
        return sign | (1 << 23)

    significand = _round_integer_right(magnitude, magnitude.bit_length() - 24)
    if significand == 1 << 24:
        significand = 1 << 23
        exact_exponent += 1
    if exact_exponent > 127:
        raise HCPreServiceNumericError("finite binary32 arithmetic overflow")
    return sign | ((exact_exponent + 127) << 23) | (significand - (1 << 23))


def _pow2(exponent: int) -> Fraction:
    if exponent >= 0:
        return Fraction(1 << exponent)
    return Fraction(1, 1 << -exponent)


def _decode_binary32_fraction(code: int) -> Fraction:
    integer, exponent = _decode_binary32_dyadic(code)
    return Fraction(integer) * _pow2(exponent)


def _round_ties_to_even_fraction(value: Fraction) -> int:
    if value < 0:  # pragma: no cover - callers pass magnitudes
        raise HCPreServiceNumericError("unsigned rounding input is negative")
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (doubled == value.denominator and quotient & 1):
        quotient += 1
    return quotient


def _floor_log2_fraction(value: Fraction) -> int:
    if value <= 0:  # pragma: no cover - guarded by encoder
        raise HCPreServiceNumericError("log2 input is not positive")
    exponent = value.numerator.bit_length() - value.denominator.bit_length()
    if value < _pow2(exponent):
        exponent -= 1
    return exponent


def _encode_binary32_fraction(value: Fraction) -> int:
    """RNE-encode an exact rational, including gradual underflow."""

    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = abs(value)
    if magnitude < _pow2(-126):
        significand = _round_ties_to_even_fraction(magnitude / _pow2(-149))
        if significand == 0:
            return 0
        if significand < 1 << 23:
            return sign | significand
        return sign | (1 << 23)

    exponent = _floor_log2_fraction(magnitude)
    significand = _round_ties_to_even_fraction(magnitude / _pow2(exponent - 23))
    if significand == 1 << 24:
        significand = 1 << 23
        exponent += 1
    if exponent > 127:
        raise HCPreServiceNumericError("finite binary32 arithmetic overflow")
    return sign | ((exponent + 127) << 23) | (significand - (1 << 23))


def _add_codes(left_code: int, right_code: int) -> int:
    if left_code == 0:
        return right_code if right_code & 0x7FFFFFFF else 0
    if right_code == 0:
        return left_code if left_code & 0x7FFFFFFF else 0
    left_integer, left_exponent = _decode_binary32_dyadic(left_code)
    right_integer, right_exponent = _decode_binary32_dyadic(right_code)
    common_exponent = min(left_exponent, right_exponent)
    exact_integer = (left_integer << (left_exponent - common_exponent)) + (
        right_integer << (right_exponent - common_exponent)
    )
    return _encode_binary32_dyadic(exact_integer, common_exponent)


def _multiply_codes(left_code: int, right_code: int) -> int:
    if left_code & 0x7FFFFFFF == 0 or right_code & 0x7FFFFFFF == 0:
        return 0
    left_integer, left_exponent = _decode_binary32_dyadic(left_code)
    right_integer, right_exponent = _decode_binary32_dyadic(right_code)
    return _encode_binary32_dyadic(
        left_integer * right_integer,
        left_exponent + right_exponent,
    )


def _fused_product_add_codes(
    accumulator_code: int,
    left_code: int,
    right_code: int,
) -> int:
    """Round exact ``accumulator + left * right`` once to binary32."""

    if left_code & 0x7FFFFFFF == 0 or right_code & 0x7FFFFFFF == 0:
        return accumulator_code if accumulator_code & 0x7FFFFFFF else 0
    left_integer, left_exponent = _decode_binary32_dyadic(left_code)
    right_integer, right_exponent = _decode_binary32_dyadic(right_code)
    product_integer = left_integer * right_integer
    product_exponent = left_exponent + right_exponent
    if accumulator_code & 0x7FFFFFFF == 0:
        return _encode_binary32_dyadic(product_integer, product_exponent)
    accumulator_integer, accumulator_exponent = _decode_binary32_dyadic(
        accumulator_code
    )
    common_exponent = min(accumulator_exponent, product_exponent)
    exact_integer = (
        accumulator_integer << (accumulator_exponent - common_exponent)
    ) + (product_integer << (product_exponent - common_exponent))
    return _encode_binary32_dyadic(exact_integer, common_exponent)


def _divide_codes(numerator_code: int, denominator_code: int) -> int:
    denominator = _decode_binary32_fraction(denominator_code)
    if denominator == 0:
        raise HCPreServiceNumericError("binary32 division denominator is zero")
    return _encode_binary32_fraction(
        _decode_binary32_fraction(numerator_code) / denominator
    )


def _negate_code(code: int) -> int:
    return 0 if code & 0x7FFFFFFF == 0 else code ^ 0x80000000


def _sum_balanced(codes: tuple[int, ...]) -> int:
    if not codes:
        raise HCPreServiceNumericError("binary32 balanced reduction is empty")
    level = codes
    while len(level) > 1:
        if len(level) & 1:
            level += (0,)
        level = tuple(
            _add_codes(level[index], level[index + 1])
            for index in range(0, len(level), 2)
        )
    return level[0]


def _sum4(codes: Sequence[int]) -> int:
    if len(codes) != HC_PRE_HC_MULT:
        raise HCPreServiceNumericError("four-element tree requires exactly 4 values")
    return _add_codes(
        _add_codes(codes[0], codes[1]),
        _add_codes(codes[2], codes[3]),
    )


def rn32_add(left_code: int, right_code: int) -> int:
    """Apply one finite binary32 RNE addition boundary."""

    left = _validate_finite_binary32(left_code, "left_code")
    right = _validate_finite_binary32(right_code, "right_code")
    return _add_codes(left, right)


def rn32_multiply(left_code: int, right_code: int) -> int:
    """Apply one finite binary32 RNE multiplication boundary."""

    left = _validate_finite_binary32(left_code, "left_code")
    right = _validate_finite_binary32(right_code, "right_code")
    return _multiply_codes(left, right)


def rn32_divide(numerator_code: int, denominator_code: int) -> int:
    """Apply one finite binary32 RNE division boundary."""

    numerator = _validate_finite_binary32(numerator_code, "numerator_code")
    denominator = _validate_finite_binary32(
        denominator_code, "denominator_code"
    )
    return _divide_codes(numerator, denominator)


def rn32_fused_product_add(
    accumulator_code: int,
    left_code: int,
    right_code: int,
) -> int:
    """Apply NUM-4.1 exact-product, one-round accumulator semantics."""

    accumulator = _validate_finite_binary32(accumulator_code, "accumulator_code")
    left = _validate_finite_binary32(left_code, "left_code")
    right = _validate_finite_binary32(right_code, "right_code")
    return _fused_product_add_codes(accumulator, left, right)


def rn32_affine(value_code: int, scale_code: int, base_code: int) -> int:
    """Apply HC_PRE's separately rounded multiply, then add, affine boundary."""

    value = _validate_finite_binary32(value_code, "value_code")
    scale = _validate_finite_binary32(scale_code, "scale_code")
    base = _validate_finite_binary32(base_code, "base_code")
    return _add_codes(_multiply_codes(value, scale), base)


def rn32_balanced_sum4(codes: Sequence[int]) -> int:
    """Apply the NUM-6.1 four-value balanced binary32 tree."""

    raw = _sequence(codes, "codes")
    if len(raw) != HC_PRE_HC_MULT:
        raise HCPreServiceNumericError("codes must contain exactly 4 values")
    validated = tuple(
        _validate_finite_binary32(code, f"codes[{index}]")
        for index, code in enumerate(raw)
    )
    return _sum4(validated)


def rn32_balanced_sum(codes: Sequence[int]) -> int:
    """Reduce one nonempty finite binary32 row through the NUM-6.1 tree."""

    raw = _sequence(codes, "codes")
    validated = tuple(
        _validate_finite_binary32(code, f"codes[{index}]")
        for index, code in enumerate(raw)
    )
    return _sum_balanced(validated)


def cr32_rsqrt(value_code: int) -> int:
    """Correctly round exact ``1 / sqrt(value)`` to binary32."""

    code = _validate_finite_binary32(value_code, "value_code")
    value = _decode_binary32_fraction(code)
    if value <= 0:
        raise HCPreServiceNumericError(
            "binary32 reciprocal-square-root input must be positive"
        )

    # Positive binary32 encodings are monotonic.  Locate the two adjacent
    # values around the exact root, then compare its exact square with the
    # rational midpoint.  No square-root approximation enters the decision.
    lower_code = 0
    upper_exclusive = _BINARY32_MAX_FINITE + 1
    while lower_code + 1 < upper_exclusive:
        candidate_code = (lower_code + upper_exclusive) // 2
        candidate = _decode_binary32_fraction(candidate_code)
        if candidate * candidate * value <= 1:
            lower_code = candidate_code
        else:
            upper_exclusive = candidate_code

    lower = _decode_binary32_fraction(lower_code)
    if lower * lower * value == 1:
        return lower_code
    if lower_code == _BINARY32_MAX_FINITE:
        raise HCPreServiceNumericError(
            "finite binary32 reciprocal-square-root overflow"
        )
    upper_code = lower_code + 1
    upper = _decode_binary32_fraction(upper_code)
    midpoint_test = ((lower + upper) / 2) ** 2 * value
    if midpoint_test < 1:
        return upper_code
    if midpoint_test > 1:
        return lower_code
    return lower_code if lower_code & 1 == 0 else upper_code


def _dyadic_decimal(code: int) -> Decimal:
    integer, exponent = _decode_binary32_dyadic(code)
    if integer == 0:
        return Decimal(0)
    negative = integer < 0
    coefficient = abs(integer)
    if exponent >= 0:
        coefficient <<= exponent
        decimal_exponent = 0
    else:
        coefficient *= 5**-exponent
        decimal_exponent = exponent
    digits = tuple(ord(character) - ord("0") for character in str(coefficient))
    return Decimal((int(negative), digits, decimal_exponent))


def _decimal_fraction(value: Decimal) -> Fraction:
    sign, digits, exponent = value.as_tuple()
    coefficient = 0
    for digit in digits:
        coefficient = coefficient * 10 + digit
    if sign:
        coefficient = -coefficient
    if exponent >= 0:
        return Fraction(coefficient * 10**exponent)
    return Fraction(coefficient, 10**-exponent)


def _exp_rational_interval(
    value_code: int, precision: int
) -> tuple[Fraction, Fraction]:
    exact_argument = _dyadic_decimal(value_code)
    with localcontext() as context:
        # Every binary32 dyadic has at most 105 exact decimal coefficient
        # digits, so the initial precision also keeps the operand exact.
        context.prec = precision
        context.Emin = MIN_EMIN
        context.Emax = MAX_EMAX
        rounded = context.exp(exact_argument)
        predecessor = context.next_minus(rounded)
        successor = context.next_plus(rounded)

    # Decimal.exp is specified to be correctly rounded, so the exact value is
    # certainly inside this deliberately conservative adjacent-value interval.
    return _decimal_fraction(predecessor), _decimal_fraction(successor)


def _certify_interval_binary32(
    interval_factory: Callable[[int], tuple[Fraction, Fraction]],
) -> int:
    precision = 192
    certified_lower: Fraction | None = None
    certified_upper: Fraction | None = None
    while True:
        lower, upper = interval_factory(precision)
        # Intersect successive certified enclosures.  This makes the retained
        # bounds monotone even though a rounded decimal center can move from
        # one side of the exact result to the other as precision increases.
        if certified_lower is not None:
            if certified_upper is None:  # pragma: no cover - local invariant
                raise HCPreServiceNumericError(
                    "transcendental interval state is incomplete"
                )
            lower = max(lower, certified_lower)
            upper = min(upper, certified_upper)
        if lower > upper:  # pragma: no cover - would violate Decimal.exp's contract
            raise HCPreServiceNumericError(
                "correctly rounded decimal exponential produced disjoint bounds"
            )
        certified_lower = lower
        certified_upper = upper
        try:
            lower_code: int | None = _encode_binary32_fraction(lower)
        except HCPreServiceNumericError:
            lower_code = None
        try:
            upper_code: int | None = _encode_binary32_fraction(upper)
        except HCPreServiceNumericError:
            upper_code = None
        if lower_code == upper_code:
            if lower_code is None:
                raise HCPreServiceNumericError(
                    "correctly rounded exponential is nonfinite binary32"
                )
            return lower_code
        # Decimal ulps strictly decrease when precision doubles.  For a
        # nonzero algebraic argument exp(x) is transcendental and cannot equal
        # a rational binary32 midpoint; rational transformations used by the
        # logistic retain that property.  The nested refinement therefore
        # terminates.  Zero is handled exactly before reaching this loop.
        precision *= 2


@lru_cache(maxsize=4096)
def _cr32_exp_validated(value_code: int) -> int:
    value = _decode_binary32_fraction(value_code)
    if value == 0:
        return _BINARY32_ONE
    if value <= -150:
        # e > 2, hence exp(value) <= exp(-150) < 2^-150, the midpoint
        # between +0 and the least positive binary32 subnormal.
        return 0
    if value >= 128:
        # e > 2 gives exp(value) > 2^128, beyond finite binary32.
        raise HCPreServiceNumericError(
            "correctly rounded exponential is nonfinite binary32"
        )
    return _certify_interval_binary32(
        lambda precision: _exp_rational_interval(value_code, precision)
    )


def cr32_exp(value_code: int) -> int:
    """Return the correctly rounded binary32 mathematical exponential.

    Underflow to positive zero is legal.  A positive input whose mathematical
    exponential rounds outside finite binary32 raises the service poison error;
    HC_PRE's stabilized exponential inputs are always nonpositive.
    """

    code = _validate_finite_binary32(value_code, "value_code")
    return _cr32_exp_validated(code)


@lru_cache(maxsize=4096)
def _cr32_sigmoid_validated(value_code: int) -> int:
    value = _decode_binary32_fraction(value_code)
    if value == 0:
        return 0x3F000000
    if value >= 25:
        # 1-sigmoid(z) = 1/(1+e^z) < 2^-25, the half-ulp distance
        # below binary32 1.0, because e > 2 and z >= 25.
        return _BINARY32_ONE
    if value <= -150:
        # sigmoid(z) < e^z < 2^-150, so the correctly rounded result is +0.
        return 0

    negative_code = _negate_code(value_code)

    def sigmoid_interval(precision: int) -> tuple[Fraction, Fraction]:
        exp_lower, exp_upper = _exp_rational_interval(negative_code, precision)
        return (
            Fraction(1, 1) / (1 + exp_upper),
            Fraction(1, 1) / (1 + exp_lower),
        )

    return _certify_interval_binary32(sigmoid_interval)


def cr32_sigmoid(value_code: int) -> int:
    """Return direct CR32 ``1 / (1 + exp(-z))`` for any finite binary32 z."""

    code = _validate_finite_binary32(value_code, "value_code")
    return _cr32_sigmoid_validated(code)


def _binary32_to_bf16(code: int) -> tuple[int, bool]:
    if code & 0x7F800000 == 0x7F800000:
        raise HCPreServiceNumericError("nonfinite binary32 cannot convert to BF16")
    upper = code >> 16
    discarded = code & 0xFFFF
    if discarded > 0x8000 or (discarded == 0x8000 and upper & 1):
        upper += 1
    saturated = upper & 0x7F80 == 0x7F80
    if saturated:
        upper = (upper & 0x8000) | 0x7F7F
    if upper & 0x7FFF == 0:
        upper = 0
    return upper, saturated


def hc_pre_branch_column(
    pre_codes: Sequence[int],
    source_bf16_codes: Sequence[int],
) -> tuple[int, bool]:
    """Apply the specified four-source branch tree to one hidden column."""

    raw_pre = _sequence(pre_codes, "pre_codes")
    raw_sources = _sequence(source_bf16_codes, "source_bf16_codes")
    if len(raw_pre) != HC_PRE_HC_MULT:
        raise HCPreServiceNumericError("pre_codes must contain exactly 4 values")
    if len(raw_sources) != HC_PRE_HC_MULT:
        raise HCPreServiceNumericError(
            "source_bf16_codes must contain exactly 4 values"
        )
    pre = tuple(
        _validate_finite_binary32(code, f"pre_codes[{index}]")
        for index, code in enumerate(raw_pre)
    )
    sources = tuple(
        _validate_finite_bf16(code, f"source_bf16_codes[{index}]")
        for index, code in enumerate(raw_sources)
    )
    products = tuple(
        _multiply_codes(coefficient, 0 if value & 0x7FFF == 0 else value << 16)
        for coefficient, value in zip(pre, sources, strict=True)
    )
    return _binary32_to_bf16(_sum4(products))


def _validate_matrix4(value: object, label: str) -> F32Matrix:
    raw_rows = _sequence(value, label)
    if len(raw_rows) != HC_PRE_HC_MULT:
        raise HCPreServiceNumericError(f"{label} must contain exactly 4 rows")
    rows: list[F32Vector] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"{label}[{row_index}]")
        if len(row) != HC_PRE_HC_MULT:
            raise HCPreServiceNumericError(
                f"{label}[{row_index}] must contain exactly 4 values"
            )
        rows.append(
            tuple(
                _validate_finite_binary32(
                    code,
                    f"{label}[{row_index}][{column_index}]",
                )
                for column_index, code in enumerate(row)
            )
        )
    return tuple(rows)


def _row_max(row: F32Vector) -> int:
    maximum = row[0]
    maximum_value = _decode_binary32_fraction(maximum)
    for candidate in row[1:]:
        candidate_value = _decode_binary32_fraction(candidate)
        if candidate_value > maximum_value:
            maximum = candidate
            maximum_value = candidate_value
    return maximum


def _sinkhorn20_validated(
    comb_z: F32Matrix,
    epsilon_code: int,
) -> tuple[F32Matrix, F32Matrix]:
    softmax_rows: list[F32Vector] = []
    for row in comb_z:
        maximum = _row_max(row)
        exponentials = tuple(
            cr32_exp(_add_codes(code, _negate_code(maximum))) for code in row
        )
        row_sum = _sum4(exponentials)
        softmax_rows.append(
            tuple(
                _add_codes(_divide_codes(code, row_sum), epsilon_code)
                for code in exponentials
            )
        )
    stable_softmax = tuple(softmax_rows)
    combination = stable_softmax

    # Column stage one immediately follows the stabilized-softmax row stage.
    column_denominators = tuple(
        _add_codes(
            _sum4(tuple(combination[source][destination] for source in range(4))),
            epsilon_code,
        )
        for destination in range(4)
    )
    combination = tuple(
        tuple(
            _divide_codes(row[destination], column_denominators[destination])
            for destination in range(4)
        )
        for row in combination
    )

    # The initial softmax/column pair is stage one, so exactly 19 pairs remain.
    for _ in range(HC_PRE_SINKHORN_ITERATIONS - 1):
        row_denominators = tuple(
            _add_codes(_sum4(row), epsilon_code) for row in combination
        )
        combination = tuple(
            tuple(_divide_codes(code, denominator) for code in row)
            for row, denominator in zip(
                combination,
                row_denominators,
                strict=True,
            )
        )
        column_denominators = tuple(
            _add_codes(
                _sum4(tuple(combination[source][destination] for source in range(4))),
                epsilon_code,
            )
            for destination in range(4)
        )
        combination = tuple(
            tuple(
                _divide_codes(row[destination], column_denominators[destination])
                for destination in range(4)
            )
            for row in combination
        )
    return stable_softmax, combination


def sinkhorn20(
    comb_z_codes: Sequence[Sequence[int]],
    *,
    hc_epsilon_binary32: int = HC_PRE_SINKHORN_EPSILON_BINARY32,
) -> tuple[F32Matrix, F32Matrix]:
    """Execute the stabilized row stage and exactly 20 row/column stages."""

    if (
        isinstance(hc_epsilon_binary32, bool)
        or not isinstance(hc_epsilon_binary32, int)
        or hc_epsilon_binary32 != HC_PRE_SINKHORN_EPSILON_BINARY32
    ):
        raise HCPreServiceNumericError(
            "hc_epsilon_binary32 must equal the qualified HC/Sinkhorn encoding "
            f"0x{HC_PRE_SINKHORN_EPSILON_BINARY32:08x}"
        )
    matrix = _validate_matrix4(comb_z_codes, "comb_z_codes")
    return _sinkhorn20_validated(matrix, hc_epsilon_binary32)


def _validate_x(value: object) -> BF16Tensor4:
    raw_batches = _sequence(value, "x_codes")
    if not raw_batches:
        raise HCPreServiceNumericError("x_codes batch extent must be positive")
    sequence_extent: int | None = None
    batches: list[tuple[BF16HCRow, ...]] = []
    for batch_index, raw_batch in enumerate(raw_batches):
        batch = _sequence(raw_batch, f"x_codes[{batch_index}]")
        if not batch:
            raise HCPreServiceNumericError("x_codes sequence extent must be positive")
        if sequence_extent is None:
            sequence_extent = len(batch)
        elif len(batch) != sequence_extent:
            raise HCPreServiceNumericError(
                "x_codes must have rectangular sequence extent"
            )
        tokens: list[BF16HCRow] = []
        for sequence_index, raw_token in enumerate(batch):
            token_label = f"x_codes[{batch_index}][{sequence_index}]"
            token = _sequence(raw_token, token_label)
            if len(token) != HC_PRE_HC_MULT:
                raise HCPreServiceNumericError(
                    f"{token_label} must contain exactly {HC_PRE_HC_MULT} HC streams"
                )
            streams: list[BF16Vector] = []
            for stream_index, raw_stream in enumerate(token):
                stream_label = f"{token_label}[{stream_index}]"
                stream = _sequence(raw_stream, stream_label)
                if len(stream) != HC_PRE_WIDTH:
                    raise HCPreServiceNumericError(
                        f"{stream_label} must contain exactly {HC_PRE_WIDTH} values"
                    )
                streams.append(
                    tuple(
                        _validate_finite_bf16(
                            code,
                            f"{stream_label}[{column_index}]",
                        )
                        for column_index, code in enumerate(stream)
                    )
                )
            tokens.append(tuple(streams))
        batches.append(tuple(tokens))

    if sequence_extent is None:  # pragma: no cover - nonempty checks above
        raise HCPreServiceNumericError("x_codes sequence extent is absent")
    token_count = len(batches) * sequence_extent
    if not 1 <= token_count <= 4:
        raise HCPreServiceNumericError(
            f"x_codes batch*sequence must be in 1..4, got {token_count}"
        )
    return tuple(batches)


def _validate_f32_vector(value: object, length: int, label: str) -> F32Vector:
    raw = _sequence(value, label)
    if len(raw) != length:
        raise HCPreServiceNumericError(f"{label} must contain exactly {length} values")
    return tuple(
        _validate_finite_binary32(code, f"{label}[{index}]")
        for index, code in enumerate(raw)
    )


def _validate_projection(value: object) -> tuple[F32Vector, ...]:
    raw_rows = _sequence(value, "hc_fn_codes")
    if len(raw_rows) != HC_PRE_MIX_FIELDS:
        raise HCPreServiceNumericError(
            f"hc_fn_codes must contain exactly {HC_PRE_MIX_FIELDS} rows"
        )
    return tuple(
        _validate_f32_vector(
            row,
            HC_PRE_FLATTENED_WIDTH,
            f"hc_fn_codes[{row_index}]",
        )
        for row_index, row in enumerate(raw_rows)
    )


def _semantic_counters(token_count: int, saturation_count: int) -> Mapping[str, int]:
    per_token = {
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
    }
    counters = {name: value * token_count for name, value in per_token.items()}
    counters["hc_pre_branch_bf16_saturations"] = saturation_count
    return MappingProxyType(counters)


def _execute_token(
    token: BF16HCRow,
    projection_weights: tuple[F32Vector, ...],
    scales: F32Vector,
    bases: F32Vector,
    norm_epsilon_code: int,
    hc_epsilon_code: int,
) -> tuple[
    BF16Vector,
    F32Vector,
    F32Matrix,
    int,
    int,
    F32Vector,
    F32Vector,
    F32Vector,
    F32Matrix,
    int,
]:
    flattened = tuple(
        0 if code & 0x7FFF == 0 else code << 16 for stream in token for code in stream
    )
    squares = tuple(_multiply_codes(code, code) for code in flattened)
    square_sum = _sum_balanced(squares)
    mean = _divide_codes(square_sum, _BINARY32_WIDTH)
    biased_mean = _add_codes(mean, norm_epsilon_code)
    inverse = cr32_rsqrt(biased_mean)

    projections: list[int] = []
    mixes: list[int] = []
    for weight_row in projection_weights:
        accumulator = 0
        for activation, weight in zip(flattened, weight_row, strict=True):
            accumulator = _fused_product_add_codes(accumulator, activation, weight)
        projections.append(accumulator)
        mixes.append(_multiply_codes(accumulator, inverse))
    projection_codes = tuple(projections)
    mix_codes = tuple(mixes)

    affine: list[int] = []
    for field_index, (mix, base) in enumerate(zip(mix_codes, bases, strict=True)):
        scale = scales[0 if field_index < 4 else 1 if field_index < 8 else 2]
        affine.append(rn32_affine(mix, scale, base))

    pre = tuple(
        _add_codes(cr32_sigmoid(affine[index]), hc_epsilon_code) for index in range(4)
    )
    post = tuple(
        _multiply_codes(_BINARY32_TWO, cr32_sigmoid(affine[4 + index]))
        for index in range(4)
    )
    comb_z = tuple(
        tuple(affine[8 + source * 4 + destination] for destination in range(4))
        for source in range(4)
    )
    stable_softmax, combination = _sinkhorn20_validated(
        comb_z,
        hc_epsilon_code,
    )

    branch: list[int] = []
    saturation_count = 0
    for column in range(HC_PRE_WIDTH):
        products = tuple(
            _multiply_codes(pre[source], flattened[source * HC_PRE_WIDTH + column])
            for source in range(4)
        )
        converted, saturated = _binary32_to_bf16(_sum4(products))
        branch.append(converted)
        saturation_count += int(saturated)

    return (
        tuple(branch),
        post,
        combination,
        mean,
        inverse,
        projection_codes,
        mix_codes,
        pre,
        stable_softmax,
        saturation_count,
    )


def execute_hc_pre(
    x_codes: Sequence[Sequence[Sequence[Sequence[int]]]],
    hc_fn_codes: Sequence[Sequence[int]],
    hc_scale_codes: Sequence[int],
    hc_base_codes: Sequence[int],
    *,
    norm_epsilon_binary32: int = HC_PRE_NORM_EPSILON_BINARY32,
    hc_epsilon_binary32: int = HC_PRE_SINKHORN_EPSILON_BINARY32,
) -> HCPreServiceResult:
    """Execute one qualified, homogeneous NUM-6.10 HC_PRE command atomically."""

    if (
        isinstance(norm_epsilon_binary32, bool)
        or not isinstance(norm_epsilon_binary32, int)
        or norm_epsilon_binary32 != HC_PRE_NORM_EPSILON_BINARY32
    ):
        raise HCPreServiceNumericError(
            "norm_epsilon_binary32 must equal the qualified RMS encoding "
            f"0x{HC_PRE_NORM_EPSILON_BINARY32:08x}"
        )
    if (
        isinstance(hc_epsilon_binary32, bool)
        or not isinstance(hc_epsilon_binary32, int)
        or hc_epsilon_binary32 != HC_PRE_SINKHORN_EPSILON_BINARY32
    ):
        raise HCPreServiceNumericError(
            "hc_epsilon_binary32 must equal the qualified HC/Sinkhorn encoding "
            f"0x{HC_PRE_SINKHORN_EPSILON_BINARY32:08x}"
        )

    # Validate and materialize every input before any result object can exist.
    # Residual uses this original BF16 payload, including signed-zero bits.
    residual = _validate_x(x_codes)
    projection_weights = _validate_projection(hc_fn_codes)
    scales = _validate_f32_vector(hc_scale_codes, 3, "hc_scale_codes")
    bases = _validate_f32_vector(
        hc_base_codes,
        HC_PRE_MIX_FIELDS,
        "hc_base_codes",
    )

    branches: list[tuple[BF16Vector, ...]] = []
    posts: list[tuple[F32Vector, ...]] = []
    combinations: list[tuple[F32Matrix, ...]] = []
    means: list[tuple[int, ...]] = []
    inverses: list[tuple[int, ...]] = []
    projections: list[tuple[F32Vector, ...]] = []
    mixes: list[tuple[F32Vector, ...]] = []
    pres: list[tuple[F32Vector, ...]] = []
    stable_softmaxes: list[tuple[F32Matrix, ...]] = []
    saturation_count = 0

    for batch_index, batch in enumerate(residual):
        batch_branches: list[BF16Vector] = []
        batch_posts: list[F32Vector] = []
        batch_combinations: list[F32Matrix] = []
        batch_means: list[int] = []
        batch_inverses: list[int] = []
        batch_projections: list[F32Vector] = []
        batch_mixes: list[F32Vector] = []
        batch_pres: list[F32Vector] = []
        batch_softmaxes: list[F32Matrix] = []
        for sequence_index, token in enumerate(batch):
            try:
                (
                    branch,
                    post,
                    combination,
                    mean,
                    inverse,
                    projection,
                    mix,
                    pre,
                    stable_softmax,
                    token_saturations,
                ) = _execute_token(
                    token,
                    projection_weights,
                    scales,
                    bases,
                    norm_epsilon_binary32,
                    hc_epsilon_binary32,
                )
            except HCPreServiceNumericError as exc:
                raise HCPreServiceNumericError(
                    f"HC_PRE token [{batch_index}][{sequence_index}] failed: {exc}"
                ) from exc
            batch_branches.append(branch)
            batch_posts.append(post)
            batch_combinations.append(combination)
            batch_means.append(mean)
            batch_inverses.append(inverse)
            batch_projections.append(projection)
            batch_mixes.append(mix)
            batch_pres.append(pre)
            batch_softmaxes.append(stable_softmax)
            saturation_count += token_saturations
        branches.append(tuple(batch_branches))
        posts.append(tuple(batch_posts))
        combinations.append(tuple(batch_combinations))
        means.append(tuple(batch_means))
        inverses.append(tuple(batch_inverses))
        projections.append(tuple(batch_projections))
        mixes.append(tuple(batch_mixes))
        pres.append(tuple(batch_pres))
        stable_softmaxes.append(tuple(batch_softmaxes))

    token_count = sum(len(batch) for batch in residual)
    return HCPreServiceResult(
        branch_codes=tuple(branches),
        post_codes=tuple(posts),
        combination_codes=tuple(combinations),
        residual_codes=residual,
        rms_mean_codes=tuple(means),
        rms_inverse_codes=tuple(inverses),
        projection_codes=tuple(projections),
        mix_codes=tuple(mixes),
        pre_codes=tuple(pres),
        stable_softmax_codes=tuple(stable_softmaxes),
        branch_saturation_count=saturation_count,
        logical_counters=_semantic_counters(token_count, saturation_count),
    )


__all__ = [
    "HC_PRE_FLATTENED_WIDTH",
    "HC_PRE_HC_MULT",
    "HC_PRE_MIX_FIELDS",
    "HC_PRE_NORM_EPSILON_BINARY32",
    "HC_PRE_SINKHORN_EPSILON_BINARY32",
    "HC_PRE_SINKHORN_ITERATIONS",
    "HC_PRE_WIDTH",
    "HCPreServiceNumericError",
    "HCPreServiceResult",
    "cr32_exp",
    "cr32_rsqrt",
    "cr32_sigmoid",
    "execute_hc_pre",
    "hc_pre_branch_column",
    "rn32_add",
    "rn32_affine",
    "rn32_balanced_sum",
    "rn32_balanced_sum4",
    "rn32_divide",
    "rn32_fused_product_add",
    "rn32_multiply",
    "sinkhorn20",
]
