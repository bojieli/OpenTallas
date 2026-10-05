#!/usr/bin/env python3
"""Build-time legality of stream-unit ops against the vector SU's lane count (W17; root 2026-10-01).

    python3 tools/v41_su_legality.py [--program results/rtl/hdc_v41x_fullshape_l0_program.hex] [--n 64] [--m 16] [--lv 7]

The vector stream unit (rtl/hdc/v41x/ot_hdc_v41x_vec.sv, W11) rejects an op at issue (c_bad -> SU fault) when
  * a reduction is combined with a scalar SFU (RSQRT, SQRT, SPSQRT, EGATE);
  * a whole/tree reduction over rows that do not flatten has a row length not a multiple of 8;
  * a SPAN reduction (the op's vectors do not fit one slot) needs more than LV span levels:
        L = ceil(log2(ceil(n / 2^ls))) > LV, ls = min(lane width of the op, slot size);
  * a gather's stride is not a power of two.
This mirrors that decision exactly (same flatten test, slot size and depth formulas) so an illegal op fails when the
PROGRAM is built -- with its PC and tag -- instead of as an SU fault in RTL.  The span bound depends on the lane
count: the full-shape attn_norm sum of squares (8 x 640 -> 5,120) needs N >= 64 (L = 7); at N = 16 it is L = 9.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402


def log2c(x: int) -> int:
    return max(0, math.ceil(math.log2(x))) if x > 1 else 0


def tzero(x: int) -> int:
    return (x & -x).bit_length() - 1


def pow2(x: int) -> bool:
    return x > 0 and x & (x - 1) == 0


def check_op(f: dict, n_lanes: int, m_lanes: int, lv: int, dyn=None) -> list[str]:
    """Reasons ot_hdc_v41x_vec would reject this SU op (empty: legal).  f: decoded fields (DYN already added)."""
    LN, LM = log2c(n_lanes), log2c(m_lanes)
    nin, nout = f["su_nin"], f["su_nout"]
    if nin == 0 or nout == 0:
        return []
    red, red_whole, red_tree = f["red"], f["red_whole"], f["red_tree"]
    aind, dst, bhalf, qm, cpair = f["a_ind"], f["dst"], f["b_half"], f["qm"], f["c_pair"]
    s1_cand = red == I.RED_NONE or red_whole or red_tree
    ni_h = nin >> 1
    s1_ok = (aind == I.IND_NONE and dst != I.DST_KVT and
             (nin % 2 == 0 or not (bhalf or qm in (I.QM_ALT_NP, I.QM_ALT_PN))) and
             f["a_so"] == nin * f["a_si"] and
             f["b_so"] == (ni_h if bhalf else nin) * f["b_si"] and
             (cpair or f["c_so"] == nin * f["c_si"]) and
             f["d_so"] == (ni_h if bhalf else nin) * f["d_si"] and
             (dst == I.DST_NONE or f["o_so"] == nin * f["o_si"]))
    wnf = (red_whole or red_tree) and red != I.RED_NONE and not s1_ok and nout > 1
    flatbad = wnf and nin % 8 != 0
    flat = s1_cand and s1_ok
    s_ni = nout * nin if flat else nin
    s_no = 1 if flat else nout
    sfu, m1 = f["sfu"], f["m1"]
    scalar = sfu in (I.SFU_RSQRT, I.SFU_SQRT, I.SFU_SPSQRT, I.SFU_EGATE)
    sfu_c = sfu in (I.SFU_EXP, I.SFU_SIGM, I.SFU_SILU) or m1 in (I.M1_DIVB, I.M1_DIVIMM)
    lvw = 0 if scalar else (LM if sfu_c else LN)
    red_on = red != I.RED_NONE
    lsz = tzero(s_ni) if wnf else log2c(max(s_ni, 8 if red_on else 1))
    ls = min(lsz, lvw)
    packed = (not wnf) and s_ni <= (1 << ls)
    nvs = s_no * (s_ni >> ls) if wnf else -(-s_ni // (1 << ls))
    L = log2c(nvs)
    span = red_on and not packed
    gather = aind != I.IND_NONE
    gstr = f["a_si"] if aind == I.IND_I else f["a_so"]
    out = []
    if red_on and scalar:
        out.append("reduction with a scalar SFU")
    if flatbad:
        out.append("unflattened whole/tree reduction with a row length not a multiple of 8")
    if span and L > lv:
        out.append(f"span depth {L} > LV {lv} ({nvs} vectors of {1 << ls} at N={n_lanes})")
    if gather and not pow2(gstr):
        out.append(f"gather stride {gstr} not a power of two")
    return out


def check_program(words: list[int], n_lanes: int, m_lanes: int, lv: int, tags=None) -> list[dict]:
    bad = []
    for pc, w in enumerate(words):
        f = I.decode(w, full_shape=True)
        if f.get("unit") != I.UNIT_SU:
            continue
        why = check_op(f, n_lanes, m_lanes, lv)
        if why:
            bad.append(dict(pc=pc, tag=(tags or {}).get(pc, ""), nout=f["su_nout"], nin=f["su_nin"], reasons=why))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--program", type=Path, default=ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.hex")
    ap.add_argument("--tags", type=Path, default=ROOT / "results/rtl/hdc_v41x_fullshape_1m_program_bind_rope_hbm.json")
    ap.add_argument("--n", type=int, default=64)
    ap.add_argument("--m", type=int, default=16)
    ap.add_argument("--lv", type=int, default=7)
    a = ap.parse_args()
    words = [int(x, 16) for x in a.program.read_text().split()]
    tags = {}
    if a.tags.exists():
        tags = {t["pc"]: t["tag"] for t in json.loads(a.tags.read_text()).get("instruction_trace", [])}
    bad = check_program(words, a.n, a.m, a.lv, tags)
    for b in bad:
        print(f"ILLEGAL pc {b['pc']} {b['tag']} nout {b['nout']} nin {b['nin']}: {'; '.join(b['reasons'])}")
    print(f"{len(bad)} illegal SU ops at N={a.n} M={a.m} LV={a.lv}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
