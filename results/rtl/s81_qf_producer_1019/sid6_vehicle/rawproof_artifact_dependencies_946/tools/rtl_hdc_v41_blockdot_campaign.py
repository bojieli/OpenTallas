#!/usr/bin/env python3
"""Bit-exact RTL simulation of the DeepSeek-V4.1 low-precision linear datapath.

The three pipelines of rtl/hdc/v41 against tools/hdc_golden_v41.py:

* ot_hdc_actquant  -- quant_fp8 (codes, scale exponent) and qdq_fp8, and
                      qdq_fp4_e8m0 (scale exponent, BF16 values; the E2M1 codes
                      are checked against the golden's own rounding);
* ot_hdc_fp4qdq    -- qdq_fp4_e4m3 (block 16);
* ot_hdc_blockdot  -- linear_q, row by row: the FP32 accumulator and the BF16
                      result, E4M3 and E2M1 weights.

Vectors come from two sources: RANDOM (seeded; distributions biased toward
every rounding, saturation, floor, subnormal and overflow edge, plus directed
ties) and REAL -- every operand the golden applies these operators to while it
decodes the first positions of the reduced model's prompt (captured by
wrapping the golden's own functions; the reduced checkpoint is read from
$OPENTALLAS_BUILD or build/).  Expected values are the golden functions'
outputs.  Where the golden's accumulator is not finite, the lane must raise
`fault` instead (it fails closed; the qualified adder never encodes an
infinity).

Runs, from the repository root: Verilator on every vector (twice for each
bench: 25 % random bubbles, and back-to-back at one block per cycle), then
Icarus (4-state) on a prefix of each vector set.  Writes
results/rtl/hdc_v41_blockdot_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402

F = np.float32
OUT = ROOT / "results/rtl/hdc_v41_blockdot_campaign.json"
RTL = [ROOT / f"rtl/hdc/v41/{n}.sv" for n in ("ot_hdc_actquant", "ot_hdc_fp4qdq", "ot_hdc_blockdot")]
LIB = [ROOT / "rtl/hdc/ot_hdc_delay.sv", ROOT / "rtl/hdc/ot_hdc_fpu.sv", ROOT / "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]
TB_Q = ROOT / "rtl/test/tb_hdc_v41_quant.sv"
TB_BD = ROOT / "rtl/test/tb_hdc_v41_blockdot.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py", Path(__file__).resolve()]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ")
ICARUS_AQ, ICARUS_Q4, ICARUS_ROWS = 4096, 4096, 1200
POSITIONS = 4                        # prompt positions decoded for the real operands
ROWS_PER_CALL = 16                   # rows sampled from each captured linear

QRE = re.compile(r"V41Q actquant vectors=(\d+) checked=(\d+) errors=(\d+) fp4qdq vectors=(\d+) checked=(\d+) "
                 r"errors=(\d+) bubbles=(\d+) cycles=(\d+)")
BRE = re.compile(r"V41BD rows=(\d+) checked=(\d+) errors=(\d+) faults_expected_and_raised=(\d+) blocks=(\d+) "
                 r"bubbles=(\d+) cycles=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def u32(x):
    return G.bits(np.asarray(x, dtype=F)).astype(np.uint64)


# -- code tables -------------------------------------------------------------------------
_E4M3_CODE = {}
for _c in range(256):
    if (_c & 0x7F) == 0x7F:
        continue
    _E4M3_CODE[(float(abs(G.E4M3[_c])), _c >> 7)] = _c


def e4m3_codes(vals):
    """float64 E4M3 values (signed zeros kept) -> codes."""
    v = np.asarray(vals, dtype=np.float64)
    return np.array([_E4M3_CODE[(abs(float(a)), int(np.signbit(a)))] for a in v], dtype=np.int64)


def e2m1_codes(vals):
    v = np.asarray(vals, dtype=np.float64)
    idx = np.searchsorted(G.E2M1_VALUES, np.abs(v))
    assert np.all(G.E2M1_VALUES[idx] == np.abs(v))
    return idx + 8 * np.signbit(v)


def hexw(ints, width_bits):
    """Little-end-first list of `width_bits`-bit fields -> one hex word (field 0 lowest)."""
    acc = 0
    for i, v in enumerate(ints):
        acc |= (int(v) & ((1 << width_bits) - 1)) << (width_bits * i)
    return acc


# -- golden references -----------------------------------------------------------------------
def aq_expect(x, fp4):
    """Expected {fault, e, codes, bf16} of one 32-element block."""
    x = np.asarray(x, dtype=F)
    if not np.all(np.isfinite(x)):
        return 1, 0, [0] * 32, [0] * 32
    if not fp4:
        q, e = G.quant_fp8(x)
        codes = e4m3_codes(q)
        y = (G.bits(G.qdq_fp8(x)) >> 16).astype(np.int64)
        return 0, int(e[0]), codes, y
    y32 = G.qdq_fp4_e8m0(x)
    # the scale and grid values, by the golden's own primitives and lines
    amax = np.maximum(np.max(np.abs(x)), G.FP4_AMAX_FLOOR_E8M0).astype(F)
    e = int(G._ceil_log2(G.mul(amax, G.FP4_MAX_INV)))
    v = np.clip(x.astype(np.float64) * np.exp2(-e), -G.FP4_MAX, G.FP4_MAX)
    q = G._round_grid(v, 0, 1)
    assert np.array_equal(G.bits(G.to_bf16((q * np.exp2(e)).astype(F))), G.bits(y32))
    return 0, e, e2m1_codes(q), (G.bits(y32) >> 16).astype(np.int64)


def q4_expect(x):
    x = np.asarray(x, dtype=F)
    if not np.all(np.isfinite(x)):
        return 1, [0] * 32
    return 0, (G.bits(G.qdq_fp4_e4m3(x, 16)) >> 16).astype(np.int64)


def linear_rows(w: G.Q8, x):
    """linear_q of every row of w: (acc FP32, BF16 result, x codes, x exps).  The
    accumulator is linear_q's own loop; the result is linear_q itself."""
    xq, xe = G.quant_fp8(x)
    n, k = w.q.shape
    acc = np.zeros(n, dtype=F)
    with np.errstate(over="ignore", invalid="ignore"):
        for b in range(k // 32):
            d = (w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F)
            acc = G.add(acc, np.ldexp(d, w.e[:, b] + xe[b]).astype(F))
        y = G.linear_q(w, x)
    finite = np.isfinite(acc)
    assert np.array_equal(G.bits(G.to_bf16(acc))[finite], G.bits(y)[finite])
    return acc, y, xq, xe


# -- coverage (what the vectors exercise; computed from exact integers, not used as expectations)
def block_coverage(cov, wq, we, xq, xe):
    """One block: exact dot in units of 2^-18, its rounding to 24 bits, and the
    scaled value's range."""
    xi = np.rint(np.asarray(xq) * 512).astype(np.int64)
    wi = np.rint(np.asarray(wq) * 512).astype(np.int64)
    S = int(np.dot(xi, wi))
    m = abs(S)
    if m == 0:
        cov["zero_block"] += 1
        return
    msb = m.bit_length() - 1
    if msb >= 24:
        drop = msb - 23
        low = m & ((1 << drop) - 1)
        if low == 1 << (drop - 1):
            cov["block_round_tie"] += 1
        elif low:
            cov["block_round_inexact"] += 1
    d = float(np.float32(S / 2.0 ** 18))
    mant, ex = np.frexp(abs(d))                      # d = mant * 2^ex, mant in [0.5, 1)
    top = ex - 1 + int(we) + int(xe)                 # exponent of the scaled value
    if top >= 128:
        cov["scaled_overflow"] += 1
    elif top < -126:
        cov["scaled_subnormal"] += 1
        mi = int(mant * 2 ** 24)                     # 24-bit significand of d
        sh = -126 - top                              # bits dropped by the subnormal rounding
        if sh <= 24:
            low = mi & ((1 << sh) - 1)
            if low == 1 << (sh - 1):
                cov["scaled_subnormal_tie"] += 1
            if (mi >> sh) + (low > 1 << (sh - 1) or (low == 1 << (sh - 1) and (mi >> sh) & 1)) == 1 << 23:
                cov["scaled_subnormal_rounds_to_min_normal"] += 1
        else:
            cov["scaled_underflow_to_zero"] += 1
    else:
        cov["scaled_normal"] += 1


def aq_coverage(cov, x, fp4):
    x = np.asarray(x, dtype=F)
    if not np.all(np.isfinite(x)):
        return
    top, mb, mine, c, fl = (6.0, 1, 0, G.FP4_MAX_INV, G.FP4_AMAX_FLOOR_E8M0) if fp4 else \
        (448.0, 3, -6, G.FP8_MAX_INV, G.FP8_AMAX_FLOOR)
    k = "fp4" if fp4 else "fp8"
    amax = np.max(np.abs(x))
    if amax < fl:
        cov[f"{k}_block_below_floor"] += 1
    e = int(G._ceil_log2(G.mul(np.maximum(amax, fl).astype(F), c)))
    v = x.astype(np.float64) * 2.0 ** -e
    a = np.abs(v)
    cov[f"{k}_saturated"] += int(np.sum(a > top))
    g = np.maximum(np.floor(np.log2(np.where(a > 0, a, 1.0))), mine)
    r = a / 2.0 ** (g - mb)
    cov[f"{k}_ties"] += int(np.sum((a <= top) & (r - np.floor(r) == 0.5)))
    cov[f"{k}_below_normal_grid"] += int(np.sum((a > 0) & (a < 2.0 ** mine)))
    cov[f"{k}_negative_to_zero"] += int(np.sum((x < 0) & (np.rint(r) == 0) & (a <= top)))
    if top * 2.0 ** e >= 2.0 ** 128 or np.any(np.round(r) * 2.0 ** (g - mb + e) >= 2.0 ** 128):
        cov[f"{k}_dequantised_overflow"] += 1


def q4_coverage(cov, x):
    x = np.asarray(x, dtype=F)
    if not np.all(np.isfinite(x)):
        return
    for h in x.reshape(2, 16):
        amax = np.maximum(np.max(np.abs(h)), G.FP4_AMAX_FLOOR_E4M3)
        t = float(amax) / 6.0
        s = float(G._e4m3_round(np.float64(t)))
        if amax < 6 * 2.0 ** -6:
            cov["scale_subnormal_e4m3"] += 1
        # the quotient sits on an E4M3 midpoint: amax * 2 / 6 is on the grid of s
        g = max(np.floor(np.log2(t)), -6)
        if (t / 2.0 ** (g - 3)) % 1 == 0.5 and float(amax) == 6 * (np.floor(t / 2.0 ** (g - 3)) + 0.5) * 2.0 ** (g - 3):
            cov["scale_ties"] += 1
        a = np.abs(h.astype(np.float64))
        cov["code_ties"] += int(np.sum(np.isin(a, G.E2M1_MIDPOINTS * s)))
        if 6.0 * s >= 2.0 ** 128:
            cov["dequantised_overflow"] += 1


# -- random operands ---------------------------------------------------------------------------
def rand_f32_bits(rng, n, emin=0, emax=254):
    s = rng.integers(0, 2, n).astype(np.uint32) << 31
    e = rng.integers(emin, emax + 1, n).astype(np.uint32) << 23
    m = rng.integers(0, 1 << 23, n).astype(np.uint32)
    return G.from_bits(s | e | m)


def random_blocks(rng, n, kinds=tuple(range(10))):
    """n 32-element blocks from a mixture of distributions."""
    out = []
    for i in range(n):
        kind = kinds[i % len(kinds)]
        if kind == 0:     # activations
            x = rng.standard_normal(32) * 10.0 ** rng.uniform(-6, 6)
        elif kind == 1:   # BF16 activations
            x = G.to_bf16((rng.standard_normal(32) * 10.0 ** rng.uniform(-3, 3)).astype(F))
        elif kind == 2:   # any finite binary32, full exponent range
            x = rand_f32_bits(rng, 32)
        elif kind == 3:   # tiny: below both floors, subnormals
            x = rand_f32_bits(rng, 32, 0, 100)
        elif kind == 4:   # a few large elements, the rest tiny or zero
            x = rng.standard_normal(32) * 1e-9
            x[rng.integers(0, 32, 3)] = rng.standard_normal(3) * 10.0 ** rng.uniform(-2, 30)
            x[rng.integers(0, 32, 4)] = rng.choice([0.0, -0.0], 4)
        elif kind == 5:   # huge: near the top of the range
            x = rand_f32_bits(rng, 32, 230, 254)
        elif kind == 6:   # zeros and negative zeros
            x = rng.choice([0.0, -0.0, 1e-45, -1e-45, 2.0 ** -126], 32)
        elif kind == 7:   # integers and exact small binary values
            x = rng.integers(-500, 500, 32) * 2.0 ** int(rng.integers(-20, 20))
        else:             # heavy tails in one block
            x = rng.standard_cauchy(32) * 10.0 ** rng.uniform(-8, 8)
        out.append(np.asarray(x, dtype=F))
    return out


def tie_blocks(rng, n, fp4):
    """Blocks whose elements sit exactly on grid points, midpoints and the
    saturation bound after scaling, and whose amax sits next to a power-of-two
    scale boundary (the saturation case)."""
    out = []
    top, mb, mine, cmax = (6.0, 1, 0, G.FP4_MAX_INV) if fp4 else (448.0, 3, -6, G.FP8_MAX_INV)
    floor = G.FP4_AMAX_FLOOR_E8M0 if fp4 else G.FP8_AMAX_FLOOR
    for _ in range(n):
        k = int(rng.integers(-60, 60)) if fp4 else int(rng.integers(-20, 60))
        # amax = top * 2^k nudged by a few ulps: the rounded amax*c may be a power of two below it
        a = F(top * 2.0 ** k)
        a = G.from_bits(G.bits(a) + np.uint32(rng.integers(0, 4)))
        amax = np.maximum(F(a), floor).astype(F)
        e = int(G._ceil_log2(G.mul(amax, cmax)))
        vals = []
        for _j in range(31):
            g = int(rng.integers(mine, (2 if fp4 else 8) + 1))
            m = int(rng.integers(0, 2 << mb)) + rng.choice([0.0, 0.5])   # grid point or midpoint
            v = (m / (1 << mb)) * 2.0 ** g * 2.0 ** e
            vals.append(v if rng.integers(0, 2) else -v)
        x = np.array([float(a)] + vals, dtype=np.float64)
        rng.shuffle(x)
        out.append(x.astype(F))
    return out


def q4_tie_blocks(rng, n):
    out = []
    for _ in range(n):
        halves = []
        for _h in range(2):
            if rng.integers(0, 2):
                sn = (int(rng.integers(1, 8)) + 0.5) * 2.0 ** -9          # subnormal-grid scale midpoint
            else:
                sn = (8 + int(rng.integers(0, 8)) + 0.5) / 8 * 2.0 ** int(rng.integers(-6, 100))
            amax = F(6.0 * sn)                                               # exact
            s = G._e4m3_round(np.float64(amax) / 6.0)
            mids = np.concatenate([G.E2M1_MIDPOINTS, G.E2M1_VALUES])
            v = rng.choice(mids, 15) * s * rng.choice([-1.0, 1.0], 15)
            h = np.concatenate([[amax], v]).astype(F)
            rng.shuffle(h)
            halves.append(h)
        out.append(np.concatenate(halves))
    return out


def random_q4(rng, n):
    xs = random_blocks(rng, n)
    for x in xs[::7]:
        x[:16] *= F(1e-3)                  # blocks of different scale in one word
    return xs


# -- real operands ---------------------------------------------------------------------------------
def capture_real(positions=POSITIONS):
    """Operands of linear_q, qdq_fp8, qdq_fp4_e8m0 and qdq_fp4_e4m3 while the golden
    decodes the first `positions` prompt positions."""
    cap = {"lin": [], "fp8": [], "e8": [], "e4": []}
    saved = {n: getattr(G, n) for n in ("linear_q", "qdq_fp8", "qdq_fp4_e8m0", "qdq_fp4_e4m3")}

    def lq(w, x):
        cap["lin"].append((w, np.asarray(x, dtype=F).copy()))
        return saved["linear_q"](w, x)

    def wrap(name, key):
        def f(x, *a):
            cap[key].append(np.asarray(x, dtype=F).copy())
            return saved[name](x, *a)
        return f

    G.linear_q = lq
    G.qdq_fp8 = wrap("qdq_fp8", "fp8")
    G.qdq_fp4_e8m0 = wrap("qdq_fp4_e8m0", "e8")
    G.qdq_fp4_e4m3 = wrap("qdq_fp4_e4m3", "e4")
    try:
        model = G.Model()
        prompt, _ = G.prompt_and_expected()
        state = model.new_state()
        for p, t in enumerate(prompt[:positions]):
            model.decode_token(t, p, state)
    finally:
        for n, f in saved.items():
            setattr(G, n, f)
    return cap


def dedupe(blocks):
    seen, out = set(), []
    for b in blocks:
        k = b.tobytes()
        if k not in seen:
            seen.add(k)
            out.append(b)
    return out


# -- vector files ------------------------------------------------------------------------------------
def build_vectors(d: Path, seed: int, n_random: int, real: bool):
    rng = np.random.default_rng(seed)
    aq, q4, rows = [], [], []          # (mode, x) ; x ; (w Q8 row-subset, x, fp4, source)
    src = {"actquant": {}, "fp4qdq": {}, "blockdot_rows": {}, "blockdot_blocks": {}}

    def add_aq(blocks, mode, tag):
        for b in blocks:
            aq.append((mode, b))
        src["actquant"][tag] = src["actquant"].get(tag, 0) + len(blocks)

    add_aq(random_blocks(rng, n_random), 0, "random_fp8")
    add_aq(random_blocks(rng, n_random), 1, "random_fp4")
    add_aq(tie_blocks(rng, n_random // 4, False), 0, "directed_ties_fp8")
    add_aq(tie_blocks(rng, n_random // 4, True), 1, "directed_ties_fp4")
    nf = [np.array([np.inf] + [1.0] * 31, dtype=F), np.array([0.0] * 31 + [-np.inf], dtype=F),
          np.array([np.nan] * 32, dtype=F)]
    add_aq(nf, 0, "nonfinite_fault")
    q4 += random_q4(rng, n_random)
    q4 += q4_tie_blocks(rng, n_random // 2)
    q4 += [np.array([np.inf] + [1.0] * 31, dtype=F)]
    src["fp4qdq"]["random"] = n_random
    src["fp4qdq"]["directed_ties"] = n_random // 2
    src["fp4qdq"]["nonfinite_fault"] = 1

    # blockdot: random rows
    def rand_q8(nrows, nb, fp4, wide):
        if fp4:
            q = G.E2M1[rng.integers(0, 16, (nrows, 32 * nb))]
        else:
            codes = rng.integers(0, 256, (nrows, 32 * nb))
            codes = np.where((codes & 0x7F) == 0x7F, codes ^ 1, codes)
            q = G.E4M3[codes]
        e = rng.integers(-127, 128, (nrows, nb)) if wide else rng.integers(-24, 8, (nrows, nb))
        return G.Q8(q.astype(np.float64), e.astype(np.int64))

    def extreme_q8(nrows, nb):
        pool = np.array([0x01, 0x81, 0x7E, 0xFE, 0x08, 0x88, 0x38, 0xB8, 0x00, 0x80, 0x07, 0x87])
        q = G.E4M3[rng.choice(pool, (nrows, 32 * nb))]
        return G.Q8(q.astype(np.float64), rng.integers(-40, 20, (nrows, nb)).astype(np.int64))

    nrand_rows = 0
    while nrand_rows < n_random:
        nb = int(rng.choice([1, 2, 3, 5, 8, 24]))
        kind = nrand_rows // 16 % 5
        x = random_blocks(rng, nb, (0, 1, 4, 6, 7, 8, 0, 1, 7, 2))
        x = np.concatenate(x)
        fp4 = False
        if kind == 0:
            w, tag = rand_q8(16, nb, False, False), "random_e4m3"
        elif kind == 1:
            w, tag, fp4 = rand_q8(16, nb, True, False), "random_e2m1", True
        elif kind == 2:
            fp4 = bool(rng.integers(0, 2))
            w, tag = rand_q8(16, nb, fp4, True), "random_wide_exponent"
        elif kind == 3:
            w, tag = extreme_q8(16, nb), "directed_extreme_codes"
        else:
            # cancellation: each row is minus its neighbour's weights on a shared x
            w = rand_q8(16, nb, False, False)
            w.q[1::2] = -w.q[0::2]
            w.e[1::2] = w.e[0::2]
            w.q[2::4, :16] = -w.q[2::4, 16:32]
            tag = "directed_cancellation"
        rows.append((w, x, fp4, tag))
        nrand_rows += 16

    # directed: blocks of a few signed power-of-two products (2^A - 2^B is a run of
    # ones: all-ones significands, ties in the block rounding and in the subnormal
    # rounding, carries into 2^-126), scaled to land near the subnormal boundary,
    # deep below it, near overflow, or in the normal range.  One row per x.
    ndir = 0
    while ndir < n_random:
        nb = int(rng.integers(1, 4))
        xs, q, e = [], [], []
        for _b in range(nb):
            xb = np.zeros(32)
            wb = np.zeros(32)
            xb[0] = 448.0                     # fixes the block's scale at 2^0
            wb[0] = rng.choice([0.0, 0.0, 1.0, -2.0 ** -9])
            idx = rng.choice(np.arange(1, 32), int(rng.integers(2, 6)), replace=False)
            for i in idx:
                xb[i] = rng.choice([-1.0, 1.0]) * 2.0 ** int(rng.integers(-9, 9))
                wb[i] = rng.choice([-1.0, 1.0]) * 2.0 ** int(rng.integers(-9, 9))
            if rng.integers(0, 3) == 0:       # a non-power product among them
                i = int(rng.choice(idx))
                xb[i] *= 1.875
                if abs(wb[i]) >= 2.0 ** -6:
                    wb[i] *= 1.75
            dot = float(np.dot(xb, wb))
            lg = int(np.floor(np.log2(abs(dot)))) if dot != 0 else 0
            target = int(rng.choice([rng.integers(-10, 10), rng.integers(-129, -122),
                                     rng.integers(-152, -130), rng.integers(124, 130)]))
            xs.append(xb)
            q.append(wb)
            e.append(target - lg)
        w = G.Q8(np.concatenate(q)[None, :], np.array([e], dtype=np.int64))
        rows.append((w, np.concatenate(xs).astype(F), False, "directed_power_terms"))
        ndir += 1

    # directed: the second (subnormal) rounding exactly on a tie, one below and one
    # above it, and all-ones significands (2^A - 2^(A-24)) that round up to 2^-126
    nsub = 0
    while nsub < n_random // 2:
        xb = np.zeros(32)
        wb = np.zeros(32)
        xb[0] = 448.0
        if nsub % 4 == 3:
            big = int(rng.integers(24, 35))                      # units 2^big - 2^(big-24)
            for i, (u, sg) in enumerate(((big, 1.0), (big - 24, -1.0))):
                a = int(rng.integers(max(-9, u - 18 - 8), min(8, u - 18 + 9) + 1))
                xb[1 + i], wb[1 + i] = 2.0 ** a, sg * 2.0 ** (u - 18 - a)
        else:
            idx = rng.choice(np.arange(1, 32), int(rng.integers(1, 5)), replace=False)
            for i in idx:
                xb[i] = rng.choice([-1.0, 1.0]) * 2.0 ** int(rng.integers(-9, 9))
                wb[i] = rng.choice([-1.0, 1.0]) * 2.0 ** int(rng.integers(-9, 9))
        dot = float(np.float32(np.dot(xb, wb)))
        if dot == 0.0:
            continue
        mant, ex = np.frexp(abs(dot))
        mi = int(mant * 2 ** 24)
        low = (mi & -mi).bit_length() - 1                        # lowest set bit of the significand
        sh = 1 if nsub % 4 == 3 else low + 1 + int(rng.integers(-1, 2)) * (nsub % 4 == 2)
        we = -126 - sh - (ex - 1)                                # scaled exponent -126 - sh
        w = G.Q8(wb[None, :], np.array([[we]], dtype=np.int64))
        rows.append((w, xb.astype(F), False, "directed_subnormal_rounding"))
        nsub += 1

    # directed: exact half-ulp ties in the block's rounding to 24 bits
    ntie = 0
    while ntie < n_random // 2:
        xb = np.zeros(32)
        wb = np.zeros(32)
        xb[0] = 448.0
        wb[0] = float(G.E4M3[int(rng.integers(0x40, 0x7F))]) * rng.choice([-1.0, 1.0])  # 2 .. 448
        big = abs(xb[0] * wb[0]) * 2.0 ** 18
        msb = int(np.floor(np.log2(big)))
        half = msb - 24                                       # the guard bit's weight, in units
        a = int(rng.integers(max(-9, half - 18 - 8), min(8, half - 18 + 9) + 1))
        xb[1], wb[1] = rng.choice([-1.0, 1.0]) * 2.0 ** a, 2.0 ** (half - 18 - a)
        extra = int(rng.integers(0, 3))                        # 0 exact tie, 1 sticky, 2 odd ulp
        if extra == 1:
            xb[2], wb[2] = 2.0 ** -9, 2.0 ** -9
        elif extra == 2 and half - 17 <= 16:
            a2 = max(-9, half + 1 - 18 - 8)
            xb[2], wb[2] = 2.0 ** a2, 2.0 ** (half + 1 - 18 - a2)
        w = G.Q8(wb[None, :], np.array([[int(rng.integers(-20, 5))]], dtype=np.int64))
        rows.append((w, xb.astype(F), False, "directed_round_ties"))
        ntie += 1

    if real:
        cap = capture_real()
        lin_x = [x for _, x in cap["lin"]]
        add_aq(dedupe([b for x in lin_x for b in np.asarray(x, dtype=F).reshape(-1, 32)]), 0,
               "real_linear_inputs_fp8")
        add_aq(dedupe([b for x in cap["fp8"] for b in x.reshape(-1, 32)]), 0, "real_qdq_fp8_window_kv")
        add_aq(dedupe([b for x in cap["e8"] for b in x.reshape(-1, 32)]), 1, "real_qdq_fp4_e8m0_index")
        real_q4 = dedupe([x.reshape(-1) for x in cap["e4"]])
        q4 += real_q4
        src["fp4qdq"]["real_compressed_kv"] = len(real_q4)
        e2m1_set = set(G.E2M1_VALUES.tolist())
        for i, (w, x) in enumerate(cap["lin"]):
            n = w.q.shape[0]
            pick = np.sort(rng.choice(n, min(n, ROWS_PER_CALL), replace=False))
            sub = G.Q8(w.q[pick], w.e[pick])
            fp4 = set(np.unique(np.abs(w.q)).tolist()) <= e2m1_set
            rows.append((sub, x, fp4, f"real_{'e2m1' if fp4 else 'e4m3'}_{w.q.shape[0]}x{w.q.shape[1]}"))

    # -- write ------------------------------------------------------------------------------------
    from collections import Counter
    cov_aq, cov_q4, cov_bd = Counter(), Counter(), Counter()
    with open(d / "aq_in.mem", "w") as fi, open(d / "aq_exp.mem", "w") as fe:
        for mode, x in aq:
            aq_coverage(cov_aq, x, mode)
            fi.write(f"{mode:01x}{hexw(G.bits(x), 32):0256x}\n")
            f, e, codes, y = aq_expect(x, mode)
            fe.write(f"{f:01x}{e & 0xFFF:03x}{hexw(codes, 8):064x}{hexw(y, 16):0128x}\n")
    with open(d / "q4_in.mem", "w") as fi, open(d / "q4_exp.mem", "w") as fe:
        for x in q4:
            q4_coverage(cov_q4, x)
            fi.write(f"{hexw(G.bits(x), 32):0256x}\n")
            f, y = q4_expect(x)
            fe.write(f"{f:01x}{hexw(y, 16):0128x}\n")
    nblk = njob = nfault = 0
    with open(d / "bd_blk.mem", "w") as fb, open(d / "bd_job.mem", "w") as fj, open(d / "bd_exp.mem", "w") as fx:
        for w, x, fp4, tag in rows:
            acc, y, xq, xe = linear_rows(w, x)
            xcodes = e4m3_codes(xq)
            nb = w.q.shape[1] // 32
            for r in range(w.q.shape[0]):
                wc = e2m1_codes(w.q[r]) if fp4 else e4m3_codes(w.q[r])
                bad = not np.isfinite(acc[r])
                fj.write(f"{nblk:08x}{nb:04x}{int(bad):04x}\n")
                fx.write(f"{int(u32(acc[r]) if not bad else 0):08x}{int(G.bits(y[r]) >> 16) if not bad else 0:04x}\n")
                for b in range(nb):
                    block_coverage(cov_bd, w.q[r, b * 32:(b + 1) * 32], w.e[r, b], xq[b * 32:(b + 1) * 32], xe[b])
                    meta = (int(fp4) << 20) | ((int(xe[b]) & 0x3FF) << 10) | (int(w.e[r, b]) & 0x3FF)
                    assert -512 <= int(xe[b]) < 512 and -512 <= int(w.e[r, b]) < 512
                    fb.write(f"{meta:08x}{hexw(xcodes[b * 32:(b + 1) * 32], 8):064x}"
                             f"{hexw(wc[b * 32:(b + 1) * 32], 8):064x}\n")
                    nblk += 1
                njob += 1
                nfault += bad
                src["blockdot_rows"][tag] = src["blockdot_rows"].get(tag, 0) + 1
                src["blockdot_blocks"][tag] = src["blockdot_blocks"].get(tag, 0) + nb
    # the Icarus prefixes: the first rows of the file are random; take a slice from the end too
    return {"actquant": len(aq), "fp4qdq": len(q4), "blockdot_rows": njob, "blockdot_blocks": nblk,
            "blockdot_rows_fault_expected": nfault, "sources": src,
            "coverage": {"actquant_elements": dict(sorted(cov_aq.items())),
                         "fp4qdq_blocks": dict(sorted(cov_q4.items())),
                         "blockdot_blocks": dict(sorted(cov_bd.items()))}}


def prefix_files(d: Path, sub: Path, naq, nq4, nrows):
    sub.mkdir()
    for name, n in (("aq_in.mem", naq), ("aq_exp.mem", naq), ("q4_in.mem", nq4), ("q4_exp.mem", nq4)):
        lines = (d / name).read_text().splitlines()
        # half from the start (random, directed), half from the end (real operands)
        pick = lines if n >= len(lines) else lines[:n // 2] + lines[-(n - n // 2):]
        (sub / name).write_text("\n".join(pick) + "\n")
    jobs = (d / "bd_job.mem").read_text().splitlines()
    exps = (d / "bd_exp.mem").read_text().splitlines()
    blks = (d / "bd_blk.mem").read_text().splitlines()
    sel = list(range(len(jobs))) if nrows >= len(jobs) else \
        list(range(nrows // 2)) + list(range(len(jobs) - (nrows - nrows // 2), len(jobs)))
    oj, ox, ob = [], [], []
    for j in sel:
        start, nb, fl = int(jobs[j][:8], 16), int(jobs[j][8:12], 16), jobs[j][12:]
        oj.append(f"{len(ob):08x}{nb:04x}{fl}")
        ox.append(exps[j])
        ob += blks[start:start + nb]
    (sub / "bd_job.mem").write_text("\n".join(oj) + "\n")
    (sub / "bd_exp.mem").write_text("\n".join(ox) + "\n")
    (sub / "bd_blk.mem").write_text("\n".join(ob) + "\n")
    return {"actquant": min(naq, len((d / "aq_in.mem").read_text().splitlines())),
            "fp4qdq": min(nq4, len((d / "q4_in.mem").read_text().splitlines())),
            "blockdot_rows": len(sel), "blockdot_blocks": len(ob)}


def saturation_check():
    """The golden clips x * 2^-e to the format maximum before rounding.  Count, over
    every finite positive binary32 amax (below the floor it is floored), the
    blocks where the clip could act: amax * 2^-e > max.  ot_hdc_actquant has no
    saturation stage because both counts are zero."""
    m = np.arange(1 << 23, dtype=np.uint32)
    out = {}
    for name, c, top, floor in (("fp8", G.FP8_MAX_INV, 448.0, G.FP8_AMAX_FLOOR),
                                ("fp4_e8m0", G.FP4_MAX_INV, G.FP4_MAX, G.FP4_AMAX_FLOOR_E8M0)):
        bad = n = 0
        for ex in range(0, 255):
            a = np.maximum(G.from_bits((np.uint32(ex) << np.uint32(23)) | m), floor).astype(F)
            e = G._ceil_log2(G.mul(a, c)).astype(np.float64)
            bad += int(np.sum(a.astype(np.float64) * np.exp2(-e) > top))
            n += a.size
        out[name] = {"amax_values_checked": n, "blocks_where_the_clip_acts": bad}
    return out


def verilator_build(tb: Path, top: str, obj: Path):
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                    "-Wno-BLKSEQ", "--top-module", top, "--prefix", "Vtb", "-Mdir", str(obj),
                    *map(str, RTL), *map(str, LIB), str(tb), str(HARNESS), "-CFLAGS", "-O1"],
                   check=True, capture_output=True)
    return obj / "Vtb"


def run(seed: int, n_random: int, real: bool) -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        vec = s / "v"
        vec.mkdir()
        counts = build_vectors(vec, seed, n_random, real)
        lint = {}
        for top in ("ot_hdc_actquant", "ot_hdc_fp4qdq", "ot_hdc_blockdot"):
            r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", top, *map(str, RTL),
                                *map(str, LIB)], capture_output=True, text=True)
            lint[top] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:20]}
        exe_q = verilator_build(TB_Q, "tb_hdc_v41_quant", s / "objq")
        exe_b = verilator_build(TB_BD, "tb_hdc_v41_blockdot", s / "objb")
        runs = []
        for bubble, sd in ((4, 11), (0, 12)):
            oq = subprocess.run([str(exe_q), f"+NAQ={counts['actquant']}", f"+NQ4={counts['fp4qdq']}",
                                 f"+BUBBLE={bubble}", f"+SEED={sd}"], cwd=vec, check=True, capture_output=True,
                                text=True).stdout
            ob = subprocess.run([str(exe_b), f"+NBLK={counts['blockdot_blocks']}",
                                 f"+NJOB={counts['blockdot_rows']}", f"+BUBBLE={bubble}", f"+SEED={sd}"],
                                cwd=vec, check=True, capture_output=True, text=True).stdout
            runs.append(("verilator", bubble, oq, ob))
        # Icarus, 4-state, on a prefix
        sub = s / "i"
        ic = prefix_files(vec, sub, ICARUS_AQ, ICARUS_Q4, ICARUS_ROWS)
        subprocess.run(["iverilog", "-g2012", "-o", str(s / "q.vvp"), "-s", "tb_hdc_v41_quant_icarus",
                        str(TB_Q), *map(str, RTL), *map(str, LIB)], check=True)
        subprocess.run(["iverilog", "-g2012", "-o", str(s / "b.vvp"), "-s", "tb_hdc_v41_blockdot_icarus",
                        str(TB_BD), *map(str, RTL), *map(str, LIB)], check=True)
        oq = subprocess.run(["vvp", "-n", str(s / "q.vvp"), f"+NAQ={ic['actquant']}", f"+NQ4={ic['fp4qdq']}",
                             "+BUBBLE=4", "+SEED=13"], cwd=sub, check=True, capture_output=True, text=True).stdout
        ob = subprocess.run(["vvp", "-n", str(s / "b.vvp"), f"+NBLK={ic['blockdot_blocks']}",
                             f"+NJOB={ic['blockdot_rows']}", "+BUBBLE=4",
                             "+SEED=13"], cwd=sub, check=True, capture_output=True, text=True).stdout
        runs.append(("icarus", 4, oq, ob))

    sims = []
    sat = saturation_check()
    ok = all(v["returncode"] == 0 for v in lint.values()) and \
        all(v["blocks_where_the_clip_acts"] == 0 for v in sat.values())
    for simulator, bubble, oq, ob in runs:
        mq, mb = QRE.search(oq), BRE.search(ob)
        q = list(map(int, mq.groups()))
        b = list(map(int, mb.groups()))
        rec = {"simulator": simulator, "bubble_probability": bubble / 16,
               "actquant": {"vectors": q[0], "checked": q[1], "mismatches": q[2]},
               "fp4qdq": {"vectors": q[3], "checked": q[4], "mismatches": q[5]},
               "quant_cycles": q[7], "quant_bubbles": q[6],
               "blockdot": {"rows": b[0], "checked": b[1], "mismatches": b[2], "faults_expected_and_raised": b[3],
                            "blocks": b[4], "bubbles": b[5], "cycles": b[6],
                            "blocks_per_cycle": round(b[4] / b[6], 4)},
               "pass": "PASS" in oq and "PASS" in ob and q[2] == 0 and q[5] == 0 and b[2] == 0
                       and q[1] == q[0] and q[4] == q[3] and b[1] == b[0]}
        ok = ok and rec["pass"]
        sims.append(rec)
    ckpt = G.CHECKPOINT
    return {
        "schema": "opentallas.hdc-v41-blockdot-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "bit-exact functional simulation of the three pipelines against the golden functions "
                          "of tools/hdc_golden_v41.py (quant_fp8, qdq_fp8, qdq_fp4_e8m0, qdq_fp4_e4m3, "
                          "linear_q); where the golden accumulator is not finite the lane must raise fault. "
                          "Clock rate is not claimed here -- see results/physical_abi3/asap7/hdc/v41.",
        "pipelines": {
            "ot_hdc_actquant": {"latency_cycles": 13, "initiation_interval": 1,
                                "per_cycle": "one 32-element block, FP8 (E4M3) or FP4 (E2M1) per block"},
            "ot_hdc_fp4qdq": {"latency_cycles": 8, "initiation_interval": 1,
                              "per_cycle": "two 16-element blocks"},
            "ot_hdc_blockdot": {"latency_cycles": 15, "initiation_interval": 1, "interleave": 8,
                                "per_cycle": "one 32-term K block of one row (32 MACs); 8 rows in flight"},
        },
        "seed": seed,
        "random_vectors_per_kind": n_random,
        "real_operands": {"enabled": real, "positions_decoded": POSITIONS if real else 0,
                          "rows_sampled_per_linear_call": ROWS_PER_CALL,
                          "checkpoint": str(ckpt.relative_to(G.BUILD)) if real else None,
                          "checkpoint_sha256": sha(ckpt) if real else None},
        "vectors": counts,
        "saturation_unreachable": sat,
        "simulations": sims,
        "verilator_lint": {"flags": list(LINT_FLAGS), "tops": lint},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p)
                         for p in (*RTL, *LIB, TB_Q, TB_BD, HARNESS, *TOOLS)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--seed", type=int, default=41)
    ap.add_argument("--random", type=int, default=12000, help="random vectors per kind")
    ap.add_argument("--no-real", action="store_true", help="skip the reduced-model operands")
    a = ap.parse_args()
    result = run(a.seed, a.random, not a.no_real)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for r in result["simulations"]:
        print(r["simulator"], "bubble", r["bubble_probability"], "actquant", r["actquant"], "fp4qdq",
              r["fp4qdq"], "blockdot", r["blockdot"], "PASS" if r["pass"] else "FAIL")
    print(result["status"], json.dumps(result["vectors"]))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
