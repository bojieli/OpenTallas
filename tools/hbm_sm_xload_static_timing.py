#!/usr/bin/env python3
"""Compiler timing model of the static SM x-load (rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static.sv).

H-ELEM-A r2 2026-10-15.  Every edge is a function of the command alone (no ready / credit); the lock bench
(rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_static_lock.sv) checks the RTL against exactly these formulas.
Edges are counted from the command edge (x_v sampled).

BF16 (fmt 0 / 3): first xw beat at 8 P + RD_LAT + 14, then gn * 8 * nb contiguous beats.
Block-dot (fmt 1 FP8 / fmt 2 FP4, streaming emission): tpair k = (g, tp) issues its P LA VM waves in a window of
WB = max(P LA, 2 nb) + 4 edges (unchanged VM read-group calendar); beat pair b of tpair k is decided at
E(k, b) = max(k WB + n(b), E_prev + 2), n(b) = min(NALL[LA][b], P LA); beat (k, b, a) is on the xw pins at
CBD + E(k, b) + a, written to x-store address ((k mod 64) * 2 + a) + x_xb, group b.
"""
from __future__ import annotations
import sys

XC = 3152
PMAX = 8
CBD = 27          # block-dot: command edge -> xw pins of a pair decided at E = 0


def nb_of(p: int) -> int:
    return (p * XC + 2047) // 2048


def nall(la: int, b: int) -> int:
    return sum(1 for p in range(PMAX) for j in range(la) if p * XC + 266 * j < 2048 * (b + 1))


def beats(p: int, fmt: int, k: int, rd_lat: int = 6, xb: int = 0) -> list[tuple[int, int, int]]:
    """[(edge, x-store address, group b)] in emission order."""
    nb = nb_of(p)
    out = []
    if fmt in (0, 3):
        gn = (k - 1) // 512 + 1
        e0 = 8 * p + rd_lat + 14
        i = 0
        for g in range(gn):
            for t in range(8):
                for b in range(nb):
                    out.append((e0 + i, ((g % 16) * 8 + t + xb) % 128, b)); i += 1
        return out
    la = 8 if fmt == 2 else 4
    gn = (k - 1) // (2048 if fmt == 2 else 1024) + 1
    wb = max(p * la, 2 * nb) + 4
    prev = -10**9
    for kk in range(gn * 4):
        for b in range(nb):
            e = max(kk * wb + min(nall(la, b), p * la), prev + 2); prev = e
            for a in range(2):
                out.append((CBD + e + a, (((kk % 64) * 2 + a) + xb) % 128, b))
    return out


def done_edge(p: int, fmt: int, k: int, rd_lat: int = 6) -> int:
    """x_done edge (one after the last beat)."""
    return beats(p, fmt, k, rd_lat)[-1][0] + 1


if __name__ == "__main__":
    # bench receipts (lock bench cmds 12..23: fmt, P, K, last beat edge)
    chk = [(1, 1, 18432, 602), (2, 8, 1120, 298), (1, 4, 576, 107), (2, 5, 2240, 377), (1, 4, 128, 107), (2, 1, 4352, 170),
           (1, 1, 1344, 90), (2, 5, 3296, 377), (1, 4, 5408, 507), (2, 1, 5536, 170), (1, 8, 1568, 314), (2, 1, 4064, 122)]
    bad = [(f, p, k, beats(p, f, k)[-1][0], e) for f, p, k, e in chk if beats(p, f, k)[-1][0] != e]
    print("model vs bench last-beat edges:", "PASS" if not bad else f"FAIL {bad}")
    sys.exit(1 if bad else 0)
