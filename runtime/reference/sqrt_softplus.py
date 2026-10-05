"""Exact deterministic target semantics for DeepSeek V4 ``SQRT_SOFTPLUS``.

The pinned ``deepseek-ai/DeepSeek-V4-Flash-0731`` source widens router inputs
and weights to binary32, computes the bias-free router projection, and then
spells the nonlinear boundary as ``F.softplus(scores).sqrt()`` in
``Gate.forward``.  PyTorch does not promise one bit-identical implementation
of those transcendental operations across every CPU and GPU backend, so this
module freezes the OpenTallas target profile explicitly:

* input and output are finite IEEE binary32 encodings;
* default PyTorch softplus parameters are preserved (``beta=1`` and a strict
  ``x > 20`` linear branch);
* the non-linear branch rounds the mathematical ``log(1 + exp(x))`` directly
  once to binary32, round-to-nearest-ties-to-even; and
* ``sqrt`` then correctly rounds the square root of that already-rounded
  binary32 softplus result once to binary32.

Exponential/logarithmic enclosures use exact rational series and square-root
selection uses exact midpoint comparisons.  No host floating-point operation,
``libm`` function, decimal approximation, compiler lowering, service engine,
or embedded answer table participates.  This is a deterministic target
adaptation for one operator, not a claim of incidental CUDA bit equivalence,
complete routing, transformer execution, RTL correctness, or PPA.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import InitVar, dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Literal, TypeAlias

from .formats import (
    NumericReferenceError,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)


OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
SOURCE_EXPRESSION = "scores = F.softplus(scores).sqrt()"
NUMERIC_PROFILE = "opentallas.deepseek_v4_sqrt_softplus_numeric.v1"

SOFTPLUS_BETA_BINARY32 = 0x3F800000  # 1.0
SOFTPLUS_THRESHOLD_BINARY32 = 0x41A00000  # 20.0
OFFICIAL_ROUTED_EXPERT_COUNT = 256
MAX_TOKENS_PER_TRANSACTION = 4

_SOFTPLUS_THRESHOLD = Fraction(20)
_PROVED_ZERO_CUTOFF = Fraction(-105)
_BINARY32_MAX_FINITE = 0x7F7FFFFF
_INITIAL_PRECISION_BITS = 48
_MAX_CACHE_ENTRIES = 65_536
_ROUNDING_CONSTRUCTION_AUTHORITY = object()

Binary32Row: TypeAlias = tuple[int, ...]
Binary32Matrix: TypeAlias = tuple[Binary32Row, ...]
SoftplusBranch: TypeAlias = Literal[
    "linear_threshold",
    "proved_underflow_zero",
    "transcendental",
]


class SqrtSoftplusReferenceError(ValueError):
    """Raised when one SQRT_SOFTPLUS transaction must poison."""


@dataclass(frozen=True)
class SqrtSoftplusRounding:
    """Every architecturally visible rounded boundary for one scalar."""

    input_binary32_code: int
    softplus_binary32_code: int
    output_binary32_code: int
    softplus_branch: SoftplusBranch
    softplus_interval_evaluations: int
    softplus_final_precision_bits: int
    sqrt_candidate_evaluations: int
    _construction_authority: InitVar[object] = None

    def __post_init__(self, _construction_authority: object) -> None:
        _validate_rounding_result(
            self,
            reconcile=_construction_authority is not _ROUNDING_CONSTRUCTION_AUTHORITY,
        )


def _finite_binary32(code: object, label: str) -> tuple[int, Fraction]:
    if type(code) is not int or not 0 <= code < 1 << 32:
        raise SqrtSoftplusReferenceError(
            f"{label} must be an exact 32-bit binary32 encoding"
        )
    try:
        decoded = decode_binary32(code)
    except NumericReferenceError as exc:  # pragma: no cover - range checked above
        raise SqrtSoftplusReferenceError(f"{label} is invalid") from exc
    if not decoded.finite or decoded.value is None:
        raise SqrtSoftplusReferenceError(f"{label} must be finite binary32")
    # The source produces the same softplus result for either zero sign.  A
    # single canonical cache key also keeps diagnostics deterministic.
    canonical = 0 if decoded.value == 0 else code
    return canonical, decoded.value


def _finite_bf16(code: object, label: str) -> int:
    if type(code) is not int or not 0 <= code < 1 << 16:
        raise SqrtSoftplusReferenceError(
            f"{label} must be an exact 16-bit BF16 encoding"
        )
    try:
        decoded = decode_bf16(code)
    except NumericReferenceError as exc:  # pragma: no cover - range checked above
        raise SqrtSoftplusReferenceError(f"{label} is invalid") from exc
    if not decoded.finite or decoded.value is None:
        raise SqrtSoftplusReferenceError(f"{label} must be finite BF16")
    return 0 if decoded.value == 0 else code


def _fraction_floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _fraction_ceil(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _exp_negative_fixed_interval(
    value: Fraction,
    precision: int,
) -> tuple[int, int]:
    """Enclose ``exp(value)`` in outward ``2**-precision`` integers.

    Range reduction places the magnitude in ``(0, 1/2]``.  Consecutive
    partial sums of the exact alternating Taylor series bracket the reduced
    exponential; outward-rounded fixed-point squaring preserves the enclosure.
    """

    if not _PROVED_ZERO_CUTOFF < value < 0:
        raise RuntimeError("negative exponential interval input is out of range")
    if precision <= 0:
        raise RuntimeError("exponential interval precision must be positive")

    magnitude = -value
    squarings = 0
    while magnitude > Fraction(1, 2):
        magnitude /= 2
        squarings += 1

    partial = Fraction(1)
    term = Fraction(1)
    lower = Fraction(0)
    upper = Fraction(1)
    target_scale = 1 << (precision + squarings + 8)
    index = 0
    while True:
        index += 1
        term = term * magnitude / index
        if index & 1:
            partial -= term
            lower = partial
            upper = partial + term
        else:
            partial += term
            upper = partial
            lower = partial - term
        if (upper - lower) * target_scale < 1:
            break

    scale = 1 << precision
    lower_fixed = _fraction_floor(lower * scale)
    upper_fixed = _fraction_ceil(upper * scale)
    for _ in range(squarings):
        lower_fixed = (lower_fixed * lower_fixed) // scale
        upper_fixed = (upper_fixed * upper_fixed + scale - 1) // scale
        upper_fixed = min(upper_fixed, scale)
    return lower_fixed, upper_fixed


def _log1p_fixed_interval(value: Fraction, precision: int) -> tuple[int, int]:
    """Enclose ``log(1 + value)`` for exact ``value`` in ``[0, 1]``.

    The identity ``log(1+y) = 2*atanh(y/(2+y))`` limits the series argument to
    ``[0, 1/3]``.  Every retained term is positive.  The omitted tail after
    exponent ``2n+1`` is bounded by replacing all later denominators with the
    first omitted denominator and summing the resulting geometric series.
    """

    if not Fraction(0) <= value <= Fraction(1):
        raise RuntimeError("log1p interval input is outside [0, 1]")
    if precision <= 0:
        raise RuntimeError("log1p interval precision must be positive")
    if value == 0:
        return 0, 0

    z = value / (2 + value)
    z_squared = z * z
    power = z
    term_index = 0
    partial = power
    scale = 1 << precision
    while True:
        first_omitted_power = power * z_squared
        first_omitted_denominator = 2 * term_index + 3
        tail = first_omitted_power / (first_omitted_denominator * (1 - z_squared))
        lower = 2 * partial
        upper = 2 * (partial + tail)
        if (upper - lower) * scale < 1:
            return (
                _fraction_floor(lower * scale),
                _fraction_ceil(upper * scale),
            )
        term_index += 1
        power = first_omitted_power
        partial += power / (2 * term_index + 1)


def _round_transcendental_softplus(value: Fraction) -> tuple[int, int, int]:
    """Return direct CR32 softplus plus exact interval diagnostics."""

    # Refinement cannot stall on a binary32 midpoint.  If the algebraic input
    # x and an algebraic midpoint m satisfied log(1+exp(x)) = m, then
    # exp(m) - exp(x) - exp(0) = 0.  The three algebraic exponents are distinct
    # (softplus(x) is positive and strictly greater than x), contradicting the
    # Lindemann-Weierstrass theorem.  Thus a finite precision eventually places
    # both outward endpoints in the same binary32 rounding cell.
    precision = _INITIAL_PRECISION_BITS
    interval_evaluations = 0
    while True:
        interval_evaluations += 1
        if value == 0:
            exp_lower = exp_upper = 1 << precision
        else:
            exp_lower, exp_upper = _exp_negative_fixed_interval(-abs(value), precision)
        scale = 1 << precision
        log_lower, _ = _log1p_fixed_interval(Fraction(exp_lower, scale), precision)
        _, log_upper = _log1p_fixed_interval(Fraction(exp_upper, scale), precision)
        lower = Fraction(log_lower, scale)
        upper = Fraction(log_upper, scale)
        if value > 0:
            lower += value
            upper += value
        try:
            lower_code = encode_binary32_rne(lower)
            upper_code = encode_binary32_rne(upper)
        except NumericReferenceError as exc:  # pragma: no cover - result <= 20
            raise SqrtSoftplusReferenceError(
                f"softplus binary32 rounding failed: {exc}"
            ) from exc
        if lower_code == upper_code:
            return lower_code, interval_evaluations, precision
        precision *= 2


def _softplus_binary32(
    value_code: int, value: Fraction
) -> tuple[int, SoftplusBranch, int, int]:
    if value > _SOFTPLUS_THRESHOLD:
        # PyTorch's default threshold branch is strict.  Its beta is exactly
        # one, so the returned binary32 score is bit-identical to the input.
        return value_code, "linear_threshold", 0, 0
    if value <= _PROVED_ZERO_CUTOFF:
        # The first five nonnegative terms prove exp(7/10) > 2, hence
        # log(2) < 7/10 and exp(-105) < 2^-150.  For x <= -105,
        # 0 < log(1+exp(x)) < exp(x) < 2^-150, the binary32 zero midpoint.
        return 0, "proved_underflow_zero", 0, 0
    code, evaluations, precision = _round_transcendental_softplus(value)
    return code, "transcendental", evaluations, precision


def _binary32_sqrt_rne(value_code: int) -> tuple[int, int]:
    """Correctly round sqrt of a nonnegative finite binary32 encoding."""

    decoded = decode_binary32(value_code)
    if not decoded.finite or decoded.value is None or decoded.value < 0:
        raise RuntimeError("softplus produced an invalid square-root input")
    value = decoded.value
    if value == 0:
        return 0, 0

    lower_code = 0
    upper_exclusive = _BINARY32_MAX_FINITE + 1
    evaluations = 0
    while lower_code + 1 < upper_exclusive:
        evaluations += 1
        candidate_code = (lower_code + upper_exclusive) // 2
        candidate = decode_binary32(candidate_code).value
        if candidate is None:  # pragma: no cover - positive finite search range
            raise RuntimeError("sqrt search reached a nonfinite candidate")
        if candidate * candidate <= value:
            lower_code = candidate_code
        else:
            upper_exclusive = candidate_code

    lower = decode_binary32(lower_code).value
    if lower is None:  # pragma: no cover - positive finite search range
        raise RuntimeError("sqrt lower candidate became nonfinite")
    lower_square = lower * lower
    if lower_square == value:
        return lower_code, evaluations
    if lower_code == _BINARY32_MAX_FINITE:  # pragma: no cover - sqrt contracts
        raise RuntimeError("finite softplus square root overflowed")

    upper_code = lower_code + 1
    upper = decode_binary32(upper_code).value
    if upper is None:  # pragma: no cover - sqrt(max finite) is far below max
        raise RuntimeError("sqrt upper candidate became nonfinite")
    midpoint = (lower + upper) / 2
    midpoint_square = midpoint * midpoint
    if value < midpoint_square:
        return lower_code, evaluations
    if value > midpoint_square:
        return upper_code, evaluations
    return (
        lower_code if lower_code & 1 == 0 else upper_code,
        evaluations,
    )


def _validate_rounding_result(
    result: SqrtSoftplusRounding,
    *,
    reconcile: bool,
) -> None:
    input_code, input_value = _finite_binary32(
        result.input_binary32_code,
        "SQRT_SOFTPLUS diagnostic input",
    )
    if input_code != result.input_binary32_code:
        raise SqrtSoftplusReferenceError(
            "SQRT_SOFTPLUS diagnostic input must use canonical positive zero"
        )
    _, softplus_value = _finite_binary32(
        result.softplus_binary32_code,
        "SQRT_SOFTPLUS diagnostic softplus result",
    )
    _, output_value = _finite_binary32(
        result.output_binary32_code,
        "SQRT_SOFTPLUS diagnostic output",
    )
    if softplus_value < 0 or output_value < 0:
        raise SqrtSoftplusReferenceError(
            "SQRT_SOFTPLUS diagnostic results must be nonnegative"
        )
    if type(result.softplus_branch) is not str or result.softplus_branch not in {
        "linear_threshold",
        "proved_underflow_zero",
        "transcendental",
    }:
        raise SqrtSoftplusReferenceError(
            "SQRT_SOFTPLUS diagnostic branch is not canonical"
        )
    for label, value in (
        ("softplus_interval_evaluations", result.softplus_interval_evaluations),
        ("softplus_final_precision_bits", result.softplus_final_precision_bits),
        ("sqrt_candidate_evaluations", result.sqrt_candidate_evaluations),
    ):
        if type(value) is not int or value < 0:
            raise SqrtSoftplusReferenceError(
                f"SQRT_SOFTPLUS diagnostic {label} must be a nonnegative integer"
            )

    if result.softplus_branch == "linear_threshold":
        structurally_valid = (
            input_value > _SOFTPLUS_THRESHOLD
            and result.softplus_binary32_code == input_code
            and result.softplus_interval_evaluations == 0
            and result.softplus_final_precision_bits == 0
        )
    elif result.softplus_branch == "proved_underflow_zero":
        structurally_valid = (
            input_value <= _PROVED_ZERO_CUTOFF
            and result.softplus_binary32_code == 0
            and result.output_binary32_code == 0
            and result.softplus_interval_evaluations == 0
            and result.softplus_final_precision_bits == 0
            and result.sqrt_candidate_evaluations == 0
        )
    else:
        precision_multiple = (
            result.softplus_final_precision_bits // _INITIAL_PRECISION_BITS
            if result.softplus_final_precision_bits >= _INITIAL_PRECISION_BITS
            else 0
        )
        structurally_valid = (
            _PROVED_ZERO_CUTOFF < input_value <= _SOFTPLUS_THRESHOLD
            and result.softplus_interval_evaluations >= 1
            and result.softplus_final_precision_bits
            == _INITIAL_PRECISION_BITS
            * (1 << (result.softplus_interval_evaluations - 1))
            and precision_multiple > 0
            and precision_multiple & (precision_multiple - 1) == 0
        )
    if not structurally_valid:
        raise SqrtSoftplusReferenceError(
            "SQRT_SOFTPLUS diagnostic branch or counters do not reconcile"
        )

    if reconcile:
        expected_softplus, expected_branch, interval_evaluations, precision = (
            _softplus_binary32(input_code, input_value)
        )
        expected_output, sqrt_evaluations = _binary32_sqrt_rne(expected_softplus)
        if (
            result.softplus_binary32_code,
            result.output_binary32_code,
            result.softplus_branch,
            result.softplus_interval_evaluations,
            result.softplus_final_precision_bits,
            result.sqrt_candidate_evaluations,
        ) != (
            expected_softplus,
            expected_output,
            expected_branch,
            interval_evaluations,
            precision,
            sqrt_evaluations,
        ):
            raise SqrtSoftplusReferenceError(
                "SQRT_SOFTPLUS diagnostic values do not match a fresh evaluation"
            )


@lru_cache(maxsize=_MAX_CACHE_ENTRIES)
def _binary32_sqrt_softplus_cached(value_code: int) -> SqrtSoftplusRounding:
    decoded = decode_binary32(value_code)
    if decoded.value is None:  # pragma: no cover - public validation invariant
        raise RuntimeError("validated SQRT_SOFTPLUS input became nonfinite")
    softplus_code, branch, interval_evaluations, precision = _softplus_binary32(
        value_code, decoded.value
    )
    output_code, sqrt_evaluations = _binary32_sqrt_rne(softplus_code)
    return SqrtSoftplusRounding(
        input_binary32_code=value_code,
        softplus_binary32_code=softplus_code,
        output_binary32_code=output_code,
        softplus_branch=branch,
        softplus_interval_evaluations=interval_evaluations,
        softplus_final_precision_bits=precision,
        sqrt_candidate_evaluations=sqrt_evaluations,
        _construction_authority=_ROUNDING_CONSTRUCTION_AUTHORITY,
    )


def binary32_sqrt_softplus_rne_with_diagnostics(
    input_binary32_code: int,
) -> SqrtSoftplusRounding:
    """Execute the two rounded Gate nonlinear stages for one finite F32 code."""

    code, _ = _finite_binary32(input_binary32_code, "SQRT_SOFTPLUS input")
    return _binary32_sqrt_softplus_cached(code)


def binary32_sqrt_softplus_rne(input_binary32_code: int) -> int:
    """Return the final binary32 ``sqrt(CR32(softplus(x)))`` encoding."""

    return binary32_sqrt_softplus_rne_with_diagnostics(
        input_binary32_code
    ).output_binary32_code


def bf16_sqrt_softplus_binary32_rne(input_bf16_code: int) -> int:
    """Exactly widen finite BF16 and execute the binary32 target operator.

    Gate receives binary32 projection scores in the architecture.  This helper
    exists for exhaustive validation over the complete finite BF16 subset of
    that input space; it does not add a BF16 architectural rounding boundary.
    """

    code = _finite_bf16(input_bf16_code, "SQRT_SOFTPLUS BF16 audit input")
    return binary32_sqrt_softplus_rne(code << 16)


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise SqrtSoftplusReferenceError(f"{label} must be an exact list or tuple")
    return value


def _materialize_score_matrix(score_binary32_codes: object) -> Binary32Matrix:
    raw_rows = _sequence(score_binary32_codes, "score_binary32_codes")
    if not raw_rows:
        raise SqrtSoftplusReferenceError(
            "score_binary32_codes must contain at least one token row"
        )
    validated: list[Binary32Row] = []
    width: int | None = None
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"score_binary32_codes[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise SqrtSoftplusReferenceError(
                    "score_binary32_codes rows must contain at least one expert"
                )
        elif len(row) != width:
            raise SqrtSoftplusReferenceError(
                "score_binary32_codes must be a rectangular rank-2 matrix"
            )
        validated.append(
            tuple(
                _finite_binary32(
                    code,
                    f"score_binary32_codes[{row_index}][{expert_index}]",
                )[0]
                for expert_index, code in enumerate(row)
            )
        )

    return tuple(validated)


def _execute_score_matrix(validated: Binary32Matrix) -> Binary32Matrix:
    return tuple(
        tuple(binary32_sqrt_softplus_rne(code) for code in row) for row in validated
    )


def sqrt_softplus_binary32(
    score_binary32_codes: Sequence[Sequence[int]],
) -> Binary32Matrix:
    """Atomically apply SQRT_SOFTPLUS to a shape-neutral audit matrix.

    The production graph entry point is :func:`sqrt_softplus_router_binary32`,
    which additionally requires the official 256-expert width and bounded
    transaction extent.  This shape-neutral helper remains useful for scalar
    and boundary qualification and makes no tensor-shape claim.
    """

    validated = _materialize_score_matrix(score_binary32_codes)
    # Validation is complete before any output container becomes observable.
    return _execute_score_matrix(validated)


def sqrt_softplus_router_binary32(
    score_binary32_codes: Sequence[Sequence[int]],
) -> Binary32Matrix:
    """Execute the official bounded ``[tokens, 256]`` router operator."""

    validated = _materialize_score_matrix(score_binary32_codes)
    if not 1 <= len(validated) <= MAX_TOKENS_PER_TRANSACTION:
        raise SqrtSoftplusReferenceError(
            f"router token extent must be in [1, {MAX_TOKENS_PER_TRANSACTION}]"
        )
    if any(len(row) != OFFICIAL_ROUTED_EXPERT_COUNT for row in validated):
        raise SqrtSoftplusReferenceError(
            "router rows must contain exactly "
            f"{OFFICIAL_ROUTED_EXPERT_COUNT} expert scores"
        )
    return _execute_score_matrix(validated)


__all__ = [
    "MODEL_SOURCE_SHA256",
    "INFERENCE_CONFIG_SHA256",
    "MAX_TOKENS_PER_TRANSACTION",
    "NUMERIC_PROFILE",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "OFFICIAL_ROUTED_EXPERT_COUNT",
    "SOFTPLUS_BETA_BINARY32",
    "SOFTPLUS_THRESHOLD_BINARY32",
    "SOURCE_EXPRESSION",
    "Binary32Matrix",
    "Binary32Row",
    "SqrtSoftplusReferenceError",
    "SqrtSoftplusRounding",
    "bf16_sqrt_softplus_binary32_rne",
    "binary32_sqrt_softplus_rne",
    "binary32_sqrt_softplus_rne_with_diagnostics",
    "sqrt_softplus_binary32",
    "sqrt_softplus_router_binary32",
]
