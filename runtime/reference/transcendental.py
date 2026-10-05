"""Exact correctly-rounded binary32 transcendental primitives.

The executable reference must not inherit a host ``libm`` implementation or a
GPU approximation at architectural nonlinear boundaries.  This module uses
exact rational interval arithmetic to enclose the mathematical exponential and
then proves which IEEE binary32 round-to-nearest-ties-to-even encoding contains
the result.

The implementation is intentionally scalar and evidence-oriented.  It is not a
performance model and it is independent of compiler lowering, service-engine
execution, and RTL.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

from .formats import NumericReferenceError, decode_binary32, encode_binary32_rne


_BINARY32_ONE = 0x3F800000
_INITIAL_PRECISION_BITS = 48
_MAX_CACHE_ENTRIES = 16_384


class TranscendentalReferenceError(ValueError):
    """Raised when a transcendental input or result poisons the transaction."""


@dataclass(frozen=True)
class TranscendentalRounding:
    """One CR32 code and the exact-interval effort needed to prove it."""

    code: int
    interval_evaluations: int
    final_precision_bits: int


def _finite_binary32(code: object, label: str) -> tuple[int, Fraction]:
    if (
        isinstance(code, bool)
        or not isinstance(code, int)
        or not 0 <= code < 1 << 32
    ):
        raise TranscendentalReferenceError(
            f"{label} must be a 32-bit binary32 encoding"
        )
    decoded = decode_binary32(code)
    if not decoded.finite or decoded.value is None:
        raise TranscendentalReferenceError(f"{label} must be finite binary32")
    return code, decoded.value


def _fraction_floor(value: Fraction) -> int:
    return value.numerator // value.denominator


def _fraction_ceil(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _exp_negative_fixed_interval(
    value: Fraction,
    precision: int,
) -> tuple[int, int]:
    """Return outward fixed-point bounds for ``exp(value)``.

    ``value`` lies strictly between -256 and zero.  Repeated halving places its
    magnitude in ``(0, 1/2]``.  The alternating Taylor series then supplies
    exact consecutive lower and upper rational bounds.  Each subsequent
    squaring rounds outward in integer fixed point, preserving enclosure.
    """

    if not Fraction(-256) < value < 0:
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


def _try_encode_binary32(value: Fraction) -> int | None:
    """Return ``None`` only when a positive finite exact value overflows."""

    try:
        return encode_binary32_rne(value)
    except NumericReferenceError as exc:
        if "overflow" not in str(exc):  # pragma: no cover - defensive boundary
            raise
        return None


def _round_exp(value: Fraction) -> TranscendentalRounding:
    if value == 0:
        return TranscendentalRounding(_BINARY32_ONE, 0, 0)

    # Since e > 2, exp(-256) < 2^-256, below the binary32 zero midpoint
    # 2^-150.  Conversely exp(256) > 2^256 and necessarily overflows.
    if value <= -256:
        return TranscendentalRounding(0, 0, 0)
    if value >= 256:
        raise TranscendentalReferenceError(
            "correctly rounded binary32 exponential overflows"
        )

    precision = _INITIAL_PRECISION_BITS
    interval_evaluations = 0
    while True:
        interval_evaluations += 1
        negative_value = value if value < 0 else -value
        lower_fixed, upper_fixed = _exp_negative_fixed_interval(
            negative_value,
            precision,
        )
        scale = 1 << precision

        if value < 0:
            lower = Fraction(lower_fixed, scale)
            upper = Fraction(upper_fixed, scale)
        else:
            # exp(x) = 1 / exp(-x).  Reciprocal monotonicity reverses the
            # bounds.  A zero lower fixed-point endpoint merely means that the
            # current precision is too coarse; doubling precision resolves it.
            if lower_fixed == 0:
                precision *= 2
                continue
            lower = Fraction(scale, upper_fixed)
            upper = Fraction(scale, lower_fixed)

        lower_code = _try_encode_binary32(lower)
        upper_code = _try_encode_binary32(upper)
        if lower_code is None:
            # lower <= exact <= upper, so overflow of the lower endpoint proves
            # overflow of the mathematical result as well.
            raise TranscendentalReferenceError(
                "correctly rounded binary32 exponential overflows"
            )
        if upper_code is not None and lower_code == upper_code:
            return TranscendentalRounding(
                lower_code,
                interval_evaluations,
                precision,
            )
        precision *= 2


@lru_cache(maxsize=_MAX_CACHE_ENTRIES)
def _binary32_exp_general_rne_cached(value_code: int) -> TranscendentalRounding:
    decoded = decode_binary32(value_code)
    if decoded.value is None:  # pragma: no cover - public validation invariant
        raise RuntimeError("validated exponential input became nonfinite")
    return _round_exp(decoded.value)


def binary32_exp_general_rne(value_code: int) -> int:
    """Return ``CR32(exp(x))`` for any finite binary32 ``x``.

    Gradual underflow to a subnormal or positive zero is legal.  A result that
    rounds beyond the maximum finite binary32 encoding is poison and raises
    :class:`TranscendentalReferenceError`.
    """

    code, _ = _finite_binary32(value_code, "binary32 exponential input")
    return _binary32_exp_general_rne_cached(code).code


def binary32_exp_general_rne_with_diagnostics(
    value_code: int,
) -> TranscendentalRounding:
    """Return general CR32 exponential plus exact-interval diagnostics."""

    code, _ = _finite_binary32(value_code, "binary32 exponential input")
    return _binary32_exp_general_rne_cached(code)


__all__ = [
    "TranscendentalReferenceError",
    "TranscendentalRounding",
    "binary32_exp_general_rne",
    "binary32_exp_general_rne_with_diagnostics",
]
