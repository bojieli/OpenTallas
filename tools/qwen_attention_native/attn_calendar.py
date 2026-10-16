#!/usr/bin/env python3
"""Per-context compiler calendar of the static native Qwen TP8 attention service (Q-VMWB / Q-ATTN, 2026-10-15).

The service takes one 176-bit calendar per request: 11 start/capture ages (edges after start_qk), field order MSB..LSB
{R, P1, P0, PV_START, HUB_PUB, HUB_RECIP, HUB_Z, HUB_LMAX, Z, LMAX, EXP} (tb_qwen_tp8_attention_native_service +CAL).
This pass derives them from the context length T (1..8192) with laws measured on the actual fix_r3 production binary
(RL21/HXK8, EPYC1 b_rl21_hxk8/parent0) at T = 1024/2048/4096/6144/8192 (EVENT ages, discovery calendar):
  all EXP committed      = EXP + 213 + T/32        (one EP pass over the T/32 keys of an engine)
  stack Z done           = Z + 2 + T/32
  pair (PV) output age   = PV_START + 590 + T/2    -> P0 = P1 = R = 590 + T/2 (static capture slots, exact)
and the component laws of the AHUB (tools/qwen_kv_die/static_ahub_calendar.py: Z issue > Z_in + 16 stride + 2,
reciprocal issue >= last Z level + 15, publish >= reciprocal return + 4).  The T-dependent minimal ages (LMAX, EXP,
Z, PV_START) come from the measured search (cal_search results); every emitted calendar is checked against the
sealed leaf rules before use (cal_bad would otherwise fault, never stretch the timeline).
"""
from __future__ import annotations

import argparse
import json
import sys

FIELDS = ("R", "P1", "P0", "PV_START", "HUB_PUB", "HUB_RECIP", "HUB_Z", "HUB_LMAX", "Z", "LMAX", "EXP")
Z_STRIDE, ZIN_D, LIN_D = 16, 2, 2
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


def ep_term(T):
    """EP pass over an engine's keys: 8 edges per started 256-key block (measured T=3000: 96, 5000: 160, 8192: 256)"""
    return 8 * ((T + 255) // 256)


def lmax_min(T):
    """QK pass end: measured minimal LMAX 152 (T=1), 183 (1000), 182 (1024), 214 (2048), 247 (3000), 278 (4096),
    364 (5000), 379 (6144), 392 (7000), 406 (8192); 150 + P2(T)/32 is the upper envelope (equal at powers of two)"""
    return 150 + p2(T) // 32


def hub(z, lmax):
    hub_lmax = lmax + 7
    hub_z = z + ZIN_D + 16 * Z_STRIDE + 2 + 1
    last = hub_z + 66                       # six Z tree levels (8,4,2,1,1,1 bursts + gap 10)
    recip = last + 15
    pub = recip + 67 + 1 + 1 + 4
    return hub_lmax, hub_z, recip, pub


def calendar(T, lmax=None, exp_gap=50, z_gap=131, pv_gap=0):
    """lmax: LMAX start (default lmax_min); exp_gap: EXP - LMAX; z_gap: Z - (EXP + 213 + ep_term); pv_gap: PV - Z"""
    if not 1 <= T <= 8192:
        raise ValueError("context 1..8192")
    if lmax is None:
        lmax = lmax_min(T)
    exp = lmax + exp_gap
    z = exp + 213 + ep_term(T) + z_gap
    pv = z + pv_gap
    hub_lmax, hub_z, recip, pub = hub(z, lmax)
    l0, l1 = pair_rows(T)
    c = dict(R=590 + max(l0, l1), P1=590 + l1, P0=590 + l0, PV_START=pv, HUB_PUB=pub, HUB_RECIP=recip, HUB_Z=hub_z, HUB_LMAX=hub_lmax, Z=z,
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
    if any(not 0 <= v < 65536 for v in c.values()):
        raise ValueError("16-bit field")


def hexcal(c):
    return "".join("%04x" % c[f] for f in FIELDS)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ctx", type=int, nargs="+", default=[8192])
    ap.add_argument("--lmax", type=int, default=None)
    ap.add_argument("--exp-gap", type=int, default=50)
    ap.add_argument("--z-gap", type=int, default=131)
    ap.add_argument("--pv-gap", type=int, default=0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    out = {}
    for T in a.ctx:
        c = calendar(T, a.lmax, a.exp_gap, a.z_gap, a.pv_gap)
        out[T] = dict(cal=hexcal(c), fields=c)
    print(json.dumps(out, indent=1) if a.json else "\n".join(f"{T} {v['cal']}" for T, v in out.items()))


if __name__ == "__main__":
    sys.exit(main())
