#!/usr/bin/env python3
"""Per-context compiler calendar of the static native Qwen TP8 attention service (Q-VMWB / Q-ATTN, 2026-10-15).

The service takes one 176-bit calendar per request: 11 start/capture ages (edges after start_qk), field order MSB..LSB
{R, P1, P0, PV_START, HUB_PUB, HUB_RECIP, HUB_Z, HUB_LMAX, Z, LMAX, EXP} (tb_qwen_tp8_attention_native_service +CAL).
Every age is derived from the context length T (1..8192) by laws read off the RTL structure and pinned by measured
fault/exact boundaries on the production binary (fix_r3 RL21/HXK8 + static ASTK CTL reading Z sums by block index,
results/arch/qwen_attention_native_calendar_1015):
  LMAX     = last ECTL QK consume (tools/qwen_kv_die/static_qk_calendar.py) + 117
  EXP      = LMAX + 15
  Z        = EXP + 250 + zwalk(T)            (EP sequencer walk position of block 0's last chunk)
  PV_START = EXP + max(75 + nblk0(T), zwalk(T) - 34), and PV_START + R >= HUB_PUB + 2
  P0/P1    = 590 + rows walked by the pair (empty pair 560), R = max(P0, P1)
  AHUB     = tools/qwen_kv_die/static_ahub_calendar.py component laws (hub()).
At each law minus one edge the service faults (observed), so the calendar is minimal; check() refuses a calendar that
breaks a sealed leaf rule (cal_bad would fault, never stretch the timeline).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FIELDS = ("R", "P1", "P0", "PV_START", "HUB_PUB", "HUB_RECIP", "HUB_Z", "HUB_LMAX", "Z", "LMAX", "EXP")
Z_STRIDE, ZIN_D, LIN_D = 16, 2, 2
ROW_LAT, QK_CONSUME, LMAX_AFTER_CONSUME = 21, 34, 117
EXP_AFTER_LMAX, Z_AFTER_EXP = 15, 250       # measured: EXP - LMAX 14 faults; Z - EXP - zwalk 249 faults
PV_EARLY, PV_WALK, RZ_MARGIN = 75, -34, 2     # PV_START - EXP >= max(75 + nblk0, zwalk - 34); PV + R >= HUB_PUB + 2
PAIR_OUT, EMPTY_PAIR_OUT = 590, 560      # pair output age after start_pv: 590 + rows (measured), an empty pair 560
# T=8192 generous calendar verified EXACT by Q-ATTN r3 (fix_r3/receipt.json)
R3_8192 = dict(R=4686, P1=4686, P0=4686, PV_START=1450, HUB_PUB=1980, HUB_RECIP=1900, HUB_Z=1711, HUB_LMAX=807,
               Z=1450, LMAX=800, EXP=850)
# measured minimal offsets (filled from the search; see MEASURED below)
MEASURED = None


def p2(T):
    p = 1
    while p < T:
        p *= 2
    return p


def pair_rows(T):
    """V rows each PV pair walks: position t goes to pair (t >> 7) & 1, walked n-major (t = 256 n + 128 p + c), so a
    pair's pass ends at its last valid slot n * 128 + c + 1 (exact; measured 591 at T=1, 2126/2054 at T=3000)"""
    L = [0, 0]
    for p in range(2):
        last = [t for t in range(min(T, 8192)) if (t >> 7) & 1 == p]
        if last:
            t = last[-1]
            L[p] = (t >> 8) * 128 + (t & 127) + 1
    return L


def zwalk(T):
    """EXP-pass position of block 0's last chunk: the ASTK EP sequencer (qkd_astk_seq) walks a stack gam-major,
    kl(gm) + 1 blocks per 8-position group gm (kl = (T - 1 - 128 S - 8 gm) >> 9); block 0 completes in the last group,
    kl(gmax - 1) + 1 steps before the end of the walk.  Max over the four stacks (block k completes k steps later and is
    read 16 k edges later, so block 0 binds)."""
    best = 0
    for S in range(4):
        base = 128 * S
        if T <= base:
            continue
        rem = T - base
        gmax = 16 if rem >= 128 else (rem + 7) >> 3
        kl = [(T - 1 - base - 8 * gm) >> 9 for gm in range(gmax)]
        best = max(best, sum(k + 1 for k in kl) - (kl[-1] + 1))
    return best


def qk_last_consume(T):
    """last QK consume age over the 32 engines (tools/qwen_kv_die/static_qk_calendar.py at RL21 / consume age 34)"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qwen_kv_die"))
    import static_qk_calendar as q
    c = q.compile_calendar(T, ROW_LAT, QK_CONSUME)
    return max(s["consume"] for e in c["engines"] for s in e["slots"])


def lmax_min(T):
    """QK pass end: LMAX >= last QK consume + LMAX_AFTER_CONSUME.  Measured on the production binary: minimal exact LMAX
    152 (T=1), 182 (1024), 214 (2048), 278 (4096), 406 (8192) and fault at last+116 for T = 100/1000/3000/5000/6144/7000
    (the lane pass is NOT T/32: ns > 1024 rows a stack scan the 2048-slot permuted ECTL order)"""
    return qk_last_consume(T) + LMAX_AFTER_CONSUME


def nblk0(T):
    """512-row blocks of stack 0 (the stack with the most blocks)"""
    return (T + 511) // 512


def pv_after_exp(T):
    """PV_START - EXP: the PV pass reads each chunk's e row a fixed number of edges after start_pv, so it may start before
    the Z sums; measured boundaries (fault below, exact at): T=1/100 75|76, 1000 76|78, 2048 78|80 -> PV_EARLY + nblk0;
    T=5000 -46|-42, 6144/7000 -42|-38, 8192 -38|-34 relative to zwalk -> zwalk + PV_WALK (the larger binds)"""
    return max(PV_EARLY + nblk0(T), zwalk(T) + PV_WALK)


def pv_min_gap(T):
    """PV_START - Z of the minimal calendar"""
    return pv_after_exp(T) - Z_AFTER_EXP - zwalk(T)


def hub(z, lmax):
    hub_lmax = lmax + 7
    hub_z = z + ZIN_D + 16 * Z_STRIDE + 2 + 1
    last = hub_z + 66                       # six Z tree levels (8,4,2,1,1,1 bursts + gap 10)
    recip = last + 15
    pub = recip + 67 + 1 + 1 + 4
    return hub_lmax, hub_z, recip, pub


def calendar(T, lmax=None, exp_gap=None, z_k=None, pv_gap=None):
    """lmax: LMAX start (default lmax_min); exp_gap: EXP - LMAX; z_k: Z - (EXP + zwalk); pv_gap: PV_START - Z"""
    if not 1 <= T <= 8192:
        raise ValueError("context 1..8192")
    if lmax is None:
        lmax = lmax_min(T)
    exp = lmax + (EXP_AFTER_LMAX if exp_gap is None else exp_gap)
    z = exp + (Z_AFTER_EXP if z_k is None else z_k) + zwalk(T)
    hub_lmax, hub_z, recip, pub = hub(z, lmax)
    l0, l1 = pair_rows(T)
    po = [PAIR_OUT + n if n else EMPTY_PAIR_OUT for n in (l0, l1)]
    if pv_gap is None:     # minimal: the e rows (EXP pass) and the published reciprocal (R capture) both bind
        pv = max(exp + pv_after_exp(T), pub + RZ_MARGIN - max(po))
    else:
        pv = z + pv_gap
    c = dict(R=max(po), P1=po[1], P0=po[0], PV_START=pv, HUB_PUB=pub, HUB_RECIP=recip, HUB_Z=hub_z, HUB_LMAX=hub_lmax, Z=z,
             LMAX=lmax, EXP=exp)
    check(c)
    return c


def check(c):
    if c["LMAX"] < 1 or c["Z"] < c["LMAX"] + 4:
        raise ValueError("ctl cal_bad: LMAX >= 1, Z >= LMAX + 4")
    if c["EXP"] <= 32:                        # EP cal_bad: exp_age <= DT + 16 (DT 16)
        raise ValueError("ep cal_bad: EXP > DT + 16")
    if c["HUB_LMAX"] <= c["LMAX"] + LIN_D + 4 or c["HUB_Z"] <= c["Z"] + ZIN_D + 16 * Z_STRIDE + 2:
        raise ValueError("ahub: issue precedes final input")
    if c["PV_START"] + c["R"] < c["HUB_PUB"] + RZ_MARGIN:
        raise ValueError("finalize rz_late: R capture precedes the published reciprocal")
    if any(not 0 <= v < 65536 for v in c.values()):
        raise ValueError("16-bit field")


def hexcal(c):
    return "".join("%04x" % c[f] for f in FIELDS)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ctx", type=int, nargs="+", default=[8192])
    ap.add_argument("--lmax", type=int, default=None)
    ap.add_argument("--exp-gap", type=int, default=None)
    ap.add_argument("--z-k", type=int, default=None)
    ap.add_argument("--pv-gap", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    out = {}
    for T in a.ctx:
        c = calendar(T, a.lmax, a.exp_gap, a.z_k, a.pv_gap)
        out[T] = dict(cal=hexcal(c), fields=c)
    print(json.dumps(out, indent=1) if a.json else "\n".join(f"{T} {v['cal']}" for T, v in out.items()))


if __name__ == "__main__":
    sys.exit(main())
