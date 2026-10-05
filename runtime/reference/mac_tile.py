"""Scalar reference for the block-floating-point MAC tile.

This is the independent authority for ``rtl/proto/ot_mac_tile.sv``. It computes
the same dot products the tile does, in Python integers, with no floating-point
arithmetic anywhere — so a disagreement is the RTL's and not a host rounding
mode's.

The arithmetic the tile implements, exactly:

* a BF16 value is ``(-1)**s * 1.f * 2**(e-127)`` with a 7-bit stored fraction, so
  its significand is the 8-bit integer ``0x80 | f`` and the product of two
  significands is **exact in 16 bits**. Nothing is rounded at the multiply.
* the product's unbiased exponent is ``ea + eb - 254``; the tile carries the
  biased sum ``ea + eb`` and compares it against a shared ``scale_exp``.
* a term whose ``rel = (ea + eb) - scale_exp`` lies in ``[0, EXP_WINDOW]`` is
  shifted left by ``rel`` into the fixed-point window and accumulated as a signed
  integer. Accumulation is therefore **exact and order-independent**: there is no
  intermediate rounding to make it otherwise.
* a term outside the window is dropped, and the tile raises that lane's
  ``dropped`` bit. This reference reports the same thing rather than hiding it.

Only the final fixed-point value is produced. Converting it back to a float is
the caller's business and is deliberately not part of this contract, so the
comparison against RTL is over integers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

#: A BF16 significand is 8 bits including the implicit leading one.
BF16_SIGNIFICAND_BITS = 8

#: The formats the lane is parameterised over, as (exponent bits, stored
#: fraction bits). The significand is fraction + 1 for the implicit leading one.
#:
#:   bf16      E8M7   activations, and what the checkpoints ship
#:   fp8_e4m3  E4M3   HBM-resident weights
#:   mxfp4     E2M1   mask-ROM-resident weights; the density thesis needs this one
FORMATS: dict[str, tuple[int, int]] = {
    "bf16": (8, 7),
    "fp8_e4m3": (4, 3),
    "mxfp4": (2, 1),
}

#: The window width the tile is parameterised with by default.
DEFAULT_EXP_WINDOW = 16


def format_parts(code: int, fmt: str) -> tuple[int, int, int]:
    """``(sign, biased exponent, significand)`` of one code in ``fmt``.

    The same unpack the RTL does for every format: a magnitude field of zero is
    an exact zero, and otherwise the significand is the stored fraction with the
    implicit leading one prepended. Widths come from :data:`FORMATS`.
    """
    if fmt not in FORMATS:
        raise ValueError(f"unknown format {fmt!r}; expected one of {sorted(FORMATS)}")
    exp_bits, frac_bits = FORMATS[fmt]
    width = 1 + exp_bits + frac_bits
    code &= (1 << width) - 1
    sign = (code >> (exp_bits + frac_bits)) & 1
    exponent = (code >> frac_bits) & ((1 << exp_bits) - 1)
    fraction = code & ((1 << frac_bits) - 1)
    if (code & ((1 << (exp_bits + frac_bits)) - 1)) == 0 or exponent == 0:
        return sign, exponent, 0
    return sign, exponent, (1 << frac_bits) | fraction


def bf16_parts(code: int) -> tuple[int, int, int]:
    """``(sign, biased exponent, 8-bit significand)`` of one BF16 code.

    A zero or subnormal code (biased exponent 0) has significand 0 here: the
    tile's ``a_zero``/``w_zero`` test is on the whole magnitude field, so it
    treats every such code as an exact zero. That is a documented narrowing of
    BF16, not an accident, and this reference matches it rather than being
    generous.
    """
    code &= 0xFFFF
    sign = (code >> 15) & 1
    exponent = (code >> 7) & 0xFF
    if (code & 0x7FFF) == 0 or exponent == 0:
        return sign, exponent, 0
    return sign, exponent, 0x80 | (code & 0x7F)


@dataclass(frozen=True)
class TileResult:
    """One lane's outcome."""

    #: The exact signed fixed-point accumulation, in window units.
    value: int
    #: True when at least one non-zero term fell outside the window.
    dropped: bool


def dot_product(
    activations: Sequence[int],
    weights: Sequence[int],
    *,
    scale_exp: int,
    exp_window: int = DEFAULT_EXP_WINDOW,
    act_format: str = "bf16",
    wgt_format: str = "bf16",
) -> TileResult:
    """One lane: the exact block-floating-point dot product the tile computes.

    ``act_format`` and ``wgt_format`` may differ, which is the point: the ROM
    design multiplies BF16 activations by MXFP4 weights, and the HBM comparator
    multiplies BF16 activations by FP8 weights.
    """
    if len(activations) != len(weights):
        raise ValueError(
            f"activation count {len(activations)} does not match weight count "
            f"{len(weights)}"
        )
    total = 0
    dropped = False
    for act, wgt in zip(activations, weights):
        a_sign, a_exp, a_man = format_parts(act, act_format)
        w_sign, w_exp, w_man = format_parts(wgt, wgt_format)
        product = a_man * w_man
        if product == 0:
            # An exact zero is not a dropped term, however far its exponent is.
            continue
        rel = (a_exp + w_exp) - scale_exp
        if rel < 0 or rel > exp_window:
            dropped = True
            continue
        magnitude = product << rel
        total += -magnitude if (a_sign ^ w_sign) else magnitude
    return TileResult(value=total, dropped=dropped)


def tile(
    activations: Sequence[int],
    weights_per_lane: Iterable[Sequence[int]],
    *,
    scale_exp: int,
    exp_window: int = DEFAULT_EXP_WINDOW,
    act_format: str = "bf16",
    wgt_format: str = "bf16",
) -> list[TileResult]:
    """Every lane of the tile, sharing one activation stream."""
    return [
        dot_product(
            activations, lane_weights, scale_exp=scale_exp,
            exp_window=exp_window, act_format=act_format, wgt_format=wgt_format,
        )
        for lane_weights in weights_per_lane
    ]


def to_twos_complement(value: int, width: int) -> int:
    """The accumulator word the RTL holds for ``value``.

    The tile accumulates in a fixed ``ACC_W``-bit window and wraps on overflow
    like any hardware adder. Wrapping here rather than raising keeps the
    reference honest: if the width is too small the comparison must FAIL and show
    the wrap, not paper over it with arbitrary precision.
    """
    return value & ((1 << width) - 1)
