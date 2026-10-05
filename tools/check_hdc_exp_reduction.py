#!/usr/bin/env python3
"""Exhaustive check of the exp range reduction in rtl/hdc/ot_hdc_sfu_q.sv.

The golden (tools/hdc_golden.exp) forms n with two binary32 adds (the 1.5*2^23
trick) and the products n*LN2_HI, n*LN2_LO with two multiplies.  The RTL forms
n = rint-to-even(t) with one integer step on t's encoding and reads both
products from a 254-entry table.  This script replays, for EVERY one of the
2^32 input words, the golden's clamp / t / u / n / products and the RTL's
integer step (bit for bit as written in ot_hdc_exp_q) and table, and requires
n, n*LN2_HI and RN(n*LN2_LO) to agree.  Everything after that point is the
same operation sequence on the same operands in both designs.

Also checks that the table in ot_hdc_sfu_q.sv is the golden's products.
"""
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402

U32 = np.uint32


def rtl_table():
    txt = (ROOT / "rtl/hdc/ot_hdc_sfu_q.sv").read_text()
    tab = {}
    for idx, hi, lo in re.findall(r"8'd(\d+)\s*: ln2_nk = \{32'h([0-9A-F]{8}), 32'h([0-9A-F]{8})\}", txt):
        tab[int(idx)] = (int(hi, 16), int(lo, 16))
    return tab


def rtl_rint(t):
    """ot_hdc_exp_q's integer step: n = rint-to-even(t) from t's encoding."""
    b = G.bits(t).astype(np.int64)
    te = (b >> 23) & 0xFF
    tm = (b & 0x7FFFFF) | 0x800000
    tsh = (23 - (((te & 31) - 31) & 31)) & 31
    tip = tm >> tsh
    trb = (tsh - 1) & 31
    thalf = (tm >> trb) & 1
    tstk = (tm & ((1 << trb) - 1)) != 0
    mag = np.where(te < 126, 0, (tip + (thalf & (tstk | (tip & 1)))) & 0xFF)
    return np.where(b >> 31 != 0, -mag, mag)


def main():
    tab = rtl_table()
    assert len(tab) == 254, len(tab)
    for k in range(-126, 128):
        nk = G.F(k)
        want = (int(G.bits(G.mul(nk, G.LN2_HI))), int(G.bits(G.mul(nk, G.LN2_LO))))
        assert tab[k & 0xFF] == want, (k, tab[k & 0xFF], want)
    hi_t = np.array([tab.get(i, (0, 0))[0] for i in range(256)], dtype=U32)
    lo_t = np.array([tab.get(i, (0, 0))[1] for i in range(256)], dtype=U32)
    step = 1 << 24
    total = bad = 0
    with np.errstate(all="ignore"):
        for start in range(0, 1 << 32, step):
            w = np.arange(start, start + step, dtype=np.uint64).astype(U32)
            x = w.view(np.float32)
            # the RTL clamp compares encodings, so NaN clamps too (to +88 / -87)
            pos = (w >> U32(31)) == 0
            mag = w & U32(0x7FFFFFFF)
            xc = np.where(pos & (mag > U32(0x42B00000)), G.F(88.0),
                          np.where(~pos & (mag > U32(0x42AE0000)), G.F(-87.0), x)).astype(np.float32)
            t = G.mul(xc, G.LOG2E)
            u = G.add(t, G.MAGIC)
            n = G.add(u, G.neg(G.MAGIC))
            g_hi, g_lo = G.bits(G.mul(n, G.LN2_HI)), G.bits(G.mul(n, G.LN2_LO))
            g_nint = (G.bits(u).astype(np.int64) & 0x1FF)
            g_nint = np.where(g_nint >= 256, g_nint - 512, g_nint)
            r_n = rtl_rint(t)
            idx = (r_n & 0xFF).astype(np.int64)
            miss = (r_n != g_nint) | (hi_t[idx] != g_hi) | (lo_t[idx] != g_lo) | (n != r_n.astype(np.float32))
            bad += int(miss.sum())
            total += len(w)
    print(f"EXP_REDUCTION words={total} mismatches={bad}")
    return 0 if bad == 0 and total == 1 << 32 else 1


if __name__ == "__main__":
    sys.exit(main())
