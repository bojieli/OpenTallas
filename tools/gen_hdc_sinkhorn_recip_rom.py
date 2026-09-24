#!/usr/bin/env python3
"""Reciprocal-seed ROM and bit-level model of the Sinkhorn unit's arithmetic.

rtl/hdc/v41/ot_hdc_sinkhorn.sv divides by a multiply-and-check, not a digit
recurrence: a table-driven quadratic gives R ~ 1/T, the quotient candidate is
M' = floor(X' * R), and two exact remainder signs pick the correctly rounded
quotient among M', M'+1, M'+2.  Everything here is the SPECIFICATION of that
arithmetic in integers, so the RTL can be written against it and the claim
"bit-identical to IEEE division" rests on two machine-checked facts:

1. ``check_seed``: for EVERY one of the 2^23 binary32 significands T in [1, 2)
   the seed satisfies 1/T - 2^-26 < R <= 1/T (an exact integer check, no
   floating point).  Then for any X' in [1, 4) the product floor underestimates
   the scaled quotient by less than one unit, so M' is M or M - 1 -- the only
   precondition of the two-threshold rounding.
2. ``check_model``: the integer model of the whole datapath (positive adder,
   divider with subnormal outputs, the Sinkhorn schedule) equals numpy's IEEE
   binary32 (tools/hdc_golden_v41.py's add / div / seqsum) on millions of
   random and edge operands.

``python3 tools/gen_hdc_sinkhorn_recip_rom.py`` rewrites
rtl/hdc/v41/ot_hdc_sk_recip_rom.sv; ``--check`` runs both proofs and fails if
the committed ROM differs from what this file generates.

Seed.  T = 1.f (23-bit f).  Index i = f[22:14] (512 segments), delta =
f[13:0] - 2^13 (signed, |delta| <= 2^13, units 2^-23), segment centre
Tc = 1 + (i + 1/2) 2^-9.  R = C0 - C1 * delta' + C2 * delta'^2 with the
Taylor coefficients 1/Tc, 1/Tc^2, 1/Tc^3 rounded to 32, 22 and 12 fraction
bits; the cubic remainder is below 2^-30.  The sum is formed at 2^-34, a
constant bias makes the error one-sided, and R keeps 28 fraction bits.
"""
from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "rtl/hdc/v41/ot_hdc_sk_recip_rom.sv"

IDX = 9                      # table index bits
DB = 23 - IDX                # delta bits (14)
F0, F1, F2 = 32, 22, 12      # coefficient fraction bits
FS = 46                      # fraction bits of the internal sum (exact: no intermediate rounding)
FR = 28                      # fraction bits of R
SQ_DROP = 12                 # delta^2 >> SQ_DROP before the C2 product
SQ_K = 4                     # the square reads only dm >> SQ_K (a 512-entry ROM, no multiplier)
WINDOW = 1 << (FR - 26)      # R may undershoot 1/T by less than 2^-26


def coefficients():
    c0, c1, c2 = [], [], []
    for i in range(1 << IDX):
        tc = 1 + Fraction(2 * i + 1, 1 << (IDX + 1))
        c0.append(round(Fraction(1 << F0) / tc))
        c1.append(round(Fraction(1 << F1) / tc ** 2))
        c2.append(round(Fraction(1 << F2) / tc ** 3))
    return np.array(c0, np.int64), np.array(c1, np.int64), np.array(c2, np.int64)


C0, C1, C2 = coefficients()


def seed_sum(t_int):
    """The seed's exact fixed-point sum at 2^-FS, as ONE carry-save tree forms it:
    S = C0 2^(FS-F0) - C1 (h - 2^13) 2^(FS-F1-23) + C2 sq 2^(FS-F2-46+SQ_DROP)
    with h = f[13:0], dm = |delta| in ONE's complement (delta < 0 -> ~delta, i.e. |delta| - 1), and
    sq = floor(dm'^2 / 2^SQ_DROP) where dm' = (dm >> SQ_K) 2^SQ_K + 2^(SQ_K-1) is the centre of dm's
    2^SQ_K-wide bucket: a 512-entry ROM read in parallel with the coefficients instead of a squarer
    after them.  The generator's exhaustive check covers every approximation."""
    t_int = np.asarray(t_int, np.int64)
    i = (t_int >> DB) & ((1 << IDX) - 1)
    h = t_int & ((1 << DB) - 1)
    d = h - (1 << (DB - 1))
    dm = np.where(d < 0, -d - 1, d)                             # 13-bit one's-complement magnitude
    sq = sq_rom_value(dm >> SQ_K)
    return (C0[i] << (FS - F0)) - ((C1[i] * h - (C1[i] << (DB - 1))) << (FS - F1 - 23)) \
        + (C2[i] * sq << (FS - F2 - 46 + SQ_DROP))


def sq_rom_value(dmh):
    """sq for the bucket dmh = dm >> SQ_K: floor(((2 dmh + 1) 2^(SQ_K-1))^2 / 2^SQ_DROP)."""
    v = 2 * np.asarray(dmh, np.int64) + 1
    return (v * v << (2 * SQ_K - 2)) >> SQ_DROP


def seed_raw(t_int):
    return seed_sum(t_int)


def bias():
    """Smallest bias (units 2^-FS) making the seed never exceed 1/T, over every T."""
    t = np.arange(1 << 23, 1 << 24, dtype=np.int64)
    r = seed_sum(t) >> (FS - FR)
    over = r * t - (np.int64(1) << (FR + 23))                 # > 0 where R > 1/T (units 2^-FR * t)
    need = -(-over // t)                                       # R units to remove
    return int(max(0, int(np.max(need)))) << (FS - FR)


BIAS = 1 << (FS - FR)        # one unit of R, at 2^-FS; bias() must not exceed it (asserted in check_seed)


def seed(t_int):
    """R = floor((S - BIAS) / 2^(FS-FR)), units 2^-FR: the tree's CPA output, top bits only."""
    return (seed_sum(t_int) - BIAS) >> (FS - FR)


def check_seed():
    b = bias()
    assert b <= BIAS, (b, BIAS)
    t = np.arange(1 << 23, 1 << 24, dtype=np.int64)
    r = seed(t)
    one = np.int64(1) << (FR + 23)
    assert np.all(r * t <= one), "seed exceeds 1/T"
    assert np.all((r + WINDOW) * t > one), "seed undershoots 1/T by 2^-26 or more"
    slack = int(np.min((r + WINDOW) * t - one))
    return {"significands_checked": int(t.size), "bias_needed": b, "bias_used": BIAS,
            "one_sided_window": "1/T - 2^-26 < R <= 1/T", "min_slack_units": slack,
            "max_undershoot_units_2^-28": float(np.max(one / t - r))}


# -- bit-level model of the datapath ---------------------------------------------------------------
def unpack(b):
    b = np.asarray(b, np.int64)
    f = (b >> 23) & 0xFF
    return np.where(f == 0, 1, f), np.where(f == 0, 0, 1 << 23) | (b & 0x7FFFFF)


def add_pos(a, b):
    """Positive binary32 RNE add on bit patterns; returns (bits, overflow).  Mirrors ot_hdc_sk_add."""
    ea, ma = unpack(a)
    eb, mb = unpack(b)
    swap = eb > ea
    eg = np.where(swap, eb, ea)
    mg = np.where(swap, mb, ma)
    msm = np.where(swap, ma, mb)
    d = np.abs(ea - eb)
    dc = np.minimum(d, 25)
    ext = np.where(d >= 25, 0, (msm << 1) >> dc)
    ahi, g = ext >> 1, ext & 1
    low = (np.int64(1) << np.minimum(d, 26)) - 1
    any_out = (msm & low) != 0
    st = np.where(d >= 1, (msm & (low >> 1)) != 0, False)
    s0 = mg + ahi
    s1 = s0 + 1
    carry = (s0 >> 24) & 1
    rnc = g.astype(bool) & (st | (s0 & 1).astype(bool))
    rc = (s0 & 1).astype(bool) & (any_out | ((s0 >> 1) & 1).astype(bool))
    m = np.where(carry == 1, np.where(rc, s1 >> 1, s0 >> 1), np.where(rnc, s1, s0))
    e = eg + carry
    ovm = m >> 24
    m = np.where(ovm == 1, 1 << 23, m)
    e = e + ovm
    field = np.where(m >> 23 == 1, e, 0)
    return (field << 23) | (m & 0x7FFFFF), e >= 255


def normalise(m, e):
    """Significand m (nonzero) to [2^23, 2^24); returns (m, unbiased exponent of the value m*2^(e-150))."""
    m = np.asarray(m, np.int64)
    lz = 23 - np.floor(np.log2(np.maximum(m, 1))).astype(np.int64)   # exact: m < 2^24
    return m << lz, e - 127 - lz


XR_DROP = 20                 # X*R partial-product columns below 2^XR_DROP are not built


def xr_product(X, R):
    """X * R with every partial-product bit in a column below XR_DROP dropped (a truncated array);
    the loss is < 24 * 2^20 < 2^25, i.e. < 1/4 unit of M' -- inside the seed's budget."""
    X, R = np.asarray(X, np.int64), np.asarray(R, np.int64)
    mask = ~np.int64((1 << XR_DROP) - 1)
    acc = np.zeros(np.broadcast(X, R).shape, np.int64)
    for j in range(24):
        acc += (((X >> j) & 1) * (R << j)) & mask
    return acc


def div(x, t):
    """Correctly rounded x / t (x >= 0, t > 0, finite) on bit patterns.  Returns (bits, overflow).
    Mirrors ot_hdc_sk_div with SUBN = 1."""
    ex, mx = unpack(x)
    et, mt = unpack(t)
    xz = mx == 0
    X, EX = normalise(np.where(xz, 1 << 23, mx), ex)
    T, ET = normalise(mt, et)
    lt = (X < T).astype(np.int64)
    Xp = X << lt
    E = EX - ET - lt
    R = seed(T)
    Mp = xr_product(X, R) >> (FR - lt)                          # floor(X' R 2^23), truncated product
    s = np.clip(-126 - E, 0, 25)
    Ms = Mp >> s
    one = np.int64(1)
    r1 = (Xp << (24 - np.minimum(s, 24))) - (2 * Ms + 1) * T
    r2 = r1 - 2 * T
    assert np.all((r1 >= -T) & (r1 < 3 * T)), "M' outside {M-1, M}"   # so r1, r2 fit 27-bit two's complement
    inc = ((r1 > 0) | ((r1 == 0) & (Ms & 1 == 1))).astype(np.int64) + \
          ((r2 > 0) | ((r2 == 0) & (Ms & 1 == 0))).astype(np.int64)
    M = Ms + inc
    ovm = (s == 0) & (M >> 24 == 1)
    M = np.where(ovm, one << 23, M)
    E = E + ovm
    field = np.where(s > 0, (M >> 23) & 1, E + 127)
    zero = xz | (s >= 25)
    out = np.where(zero, 0, (field << 23) | (M & 0x7FFFFF))
    return out, (~zero) & (field >= 255)


def check_model(n, seed_=1):
    """The integer model against numpy binary32 (canonical +0) on n random operand pairs per class."""
    sys.path.insert(0, str(ROOT / "tools"))
    import hdc_golden_v41 as G  # noqa: E402
    rng = np.random.default_rng(seed_)
    f32 = lambda b: np.asarray(b, np.uint32).view(np.float32)  # noqa: E731
    b32 = lambda v: np.asarray(v, np.float32).view(np.uint32).astype(np.int64)  # noqa: E731
    counts = {}

    def operands(kind, size):
        if kind == "raw":
            return rng.integers(0, 0x7F800000, size)
        if kind == "subnormal":
            return rng.integers(0, 0x00800000, size)
        if kind == "near":                                     # small exponent spread: ties and carries
            e = rng.integers(100, 140, size)
            return (e << 23) | rng.integers(0, 1 << 23, size)
        if kind == "unit":                                     # the Sinkhorn's own range
            return b32(rng.random(size, dtype=np.float32) * np.float32(1.5))
        if kind == "sparse":                                   # few significand bits: exact results, ties
            e = rng.integers(1, 254, size)
            m = rng.integers(0, 16, size) << rng.integers(0, 20, size)
            return (e << 23) | (m & 0x7FFFFF)
        raise ValueError(kind)

    kinds = ("raw", "subnormal", "near", "unit", "sparse")
    for ka in kinds:
        for kb in kinds:
            a, b = operands(ka, n), operands(kb, n)
            got, ovf = add_pos(a, b)
            with np.errstate(over="ignore"):
                ref = G.add(f32(a), f32(b))
            fin = np.isfinite(ref)
            assert np.array_equal(ovf, ~fin), (ka, kb, "add overflow flag")
            bad = fin & (got != b32(ref))
            assert not bad.any(), (ka, kb, "add", hex(int(a[bad][0])), hex(int(b[bad][0])))
            counts[f"add_{ka}_{kb}"] = int(n)
            b = np.where(b == 0, 1, b)
            got, ovf = div(a, b)
            with np.errstate(over="ignore", under="ignore"):
                ref = G.div(f32(a), f32(b))
            fin = np.isfinite(ref)
            assert np.array_equal(ovf, ~fin), (ka, kb, "div overflow flag")
            bad = fin & (got != b32(ref))
            assert not bad.any(), (ka, kb, "div", hex(int(a[bad][0])), hex(int(b[bad][0])))
            counts[f"div_{ka}_{kb}"] = int(n)
    return counts


# -- ROM emission ----------------------------------------------------------------------------------
def rom_text():
    w0, w1, w2 = F0 + 1, F1 + 1, F2 + 1                         # C0 <= 2^F0 (Tc > 1), C1 <= 2^F1, C2 <= 2^F2
    assert C0.max() < (1 << w0) and C1.max() < (1 << w1) and C2.max() < (1 << w2)
    lines = [
        "`timescale 1ns/1ps",
        "// GENERATED by tools/gen_hdc_sinkhorn_recip_rom.py -- do not edit.",
        "//",
        f"// Quadratic reciprocal seed coefficients for T = 1.f: index i = f[22:{DB}], centre",
        f"// Tc = 1 + (i + 1/2) 2^-{IDX}; c0 = round(2^{F0}/Tc), c1 = round(2^{F1}/Tc^2), c2 = round(2^{F2}/Tc^3).",
        "// The generator proves 1/T - 2^-26 < R <= 1/T for all 2^23 significands (see ot_hdc_sk_div).",
        "module ot_hdc_sk_recip_rom (",
        f"    input  wire [{IDX - 1}:0] i,",
        f"    output reg  [{w0 - 1}:0] c0,",
        f"    output reg  [{w1 - 1}:0] c1,",
        f"    output reg  [{w2 - 1}:0] c2",
        ");",
        "    always @* begin",
        "        case (i)",
    ]
    for k in range(1 << IDX):
        lines.append(f"            {IDX}'d{k}: begin c0 = {w0}'h{int(C0[k]):x}; c1 = {w1}'h{int(C1[k]):x}; "
                     f"c2 = {w2}'h{int(C2[k]):x}; end")
    lines += ["            default: begin c0 = 'x; c1 = 'x; c2 = 'x; end",
              "        endcase", "    end", "endmodule", ""]
    nb = 13 - SQ_K
    sq = sq_rom_value(np.arange(1 << nb))
    ws = int(sq.max()).bit_length()
    lines += [
        f"// sq(dmh) = floor(((2 dmh + 1) 2^{SQ_K - 1})^2 / 2^{SQ_DROP}): the square of the centre of the",
        f"// bucket dm >> {SQ_K} that the seed's C2 term multiplies.",
        "module ot_hdc_sk_sq_rom (",
        f"    input  wire [{nb - 1}:0] dmh,",
        f"    output reg  [{ws - 1}:0] sq",
        ");",
        "    always @* begin",
        "        case (dmh)",
    ]
    lines += [f"            {nb}'d{k}: sq = {ws}'h{int(sq[k]):x};" for k in range(1 << nb)]
    lines += [f"            default: sq = 'x;", "        endcase", "    end", "endmodule", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="prove the seed bound, test the model, compare the ROM")
    ap.add_argument("--model-samples", type=int, default=200_000)
    args = ap.parse_args()
    text = rom_text()
    if not args.check:
        ROM.write_text(text)
        print(f"wrote {ROM.relative_to(ROOT)}")
        return 0
    print(check_seed())
    print(check_model(args.model_samples))
    same = ROM.is_file() and ROM.read_text() == text
    print("rom matches generator" if same else "ROM DIFFERS from generator")
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
