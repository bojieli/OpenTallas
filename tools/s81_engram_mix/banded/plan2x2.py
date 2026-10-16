#!/usr/bin/env python3
"""Compact 2x2 start placement of one BANDED MIX4 copy cluster inside one slot-A quarter (1431.648 x 913.14 um, VM on
the E face: S-DIE joint candidate d0323e2d2 puts a quarter's 3,183 VM pins at local y 74.7..838.4).

Each band is a compact block 384.48 x 354.24 (R0 leaves; S in / N out): add8 + shell payload leaf shcol_b (lane-ordered
N face) side by side at the bottom, the mul4 pair above, chunk8 r0 r1 r2 + the two top band relays above that.  Blocks
c0 c1 form row A over the bottom feed channel, c2 c3 row B over the mid feed channel (each shcol_b's VM face S lies on
its row's channel).  The spine (sums, norms, control, gate, relays, shell control, bottom band relays) sits between the
W blocks (c0, c2) and the E blocks (c1, c3), split by the mid channel; the E region (x >= ~1158) is reserved for the VM capture tiles and the N-S cross-quarter transport.
"""
import json, sys
from pathlib import Path
G = 21.6
MW, MH = 181.44, 120.96; CW, CH = 90.72, 90.72; AW, AH = 181.44, 99.36; SW, SH = 164.16, 54.0; RW, RH = 43.2, 21.6
BW = 2 * MW + G; BH = AH + G + MH + G + CH        # 384.48 x 354.24
QW, QH = 1431.648, 913.14


def block(P, c, x0, y0):
    P[f'g_add[{c}].leaf'] = (x0, y0); P[f'col[{c}].u'] = (x0 + AW + G, y0)
    P[f'g_mult[{2*c}].leaf'] = (x0, y0 + AH + G); P[f'g_mult[{2*c+1}].leaf'] = (x0 + MW + G, y0 + AH + G)
    yc = y0 + AH + G + MH + G
    for r in range(3):
        P[f'g_reduce[{r}].g_chunk[{c}].leaf'] = (x0 + r * (CW + G), yc)
    P[f'band[{c}].rt0'] = (x0 + 3 * (CW + G), yc); P[f'band[{c}].rt1'] = (x0 + 3 * (CW + G), yc + RH + G)


def main():
    out = Path(sys.argv[1]); sw = float(sys.argv[2]) if len(sys.argv) > 2 else 302.4; ch = float(sys.argv[3]) if len(sys.argv) > 3 else 86.4
    P = {}
    lx = G; s0 = lx + BW + G; rx = s0 + sw + G
    ya = ch; yb = ya + BH + ch
    block(P, 0, lx, ya); block(P, 1, rx, ya); block(P, 2, lx, yb); block(P, 3, rx, yb)
    east = rx + BW
    sp = [('hsum', CW, 99.36), ('ksum', CW, 99.36), ('dsum', CW, 99.36), ('g_norm[0].leaf', MW, 95.04), ('g_norm[1].leaf', MW, 95.04),
          ('gate_leaf.sigmoid', MW, 110.16), ('gate_leaf.magnitude', 64.8, 43.2), ('control', CW, 64.8), ('relay', RW, RH),
          ('rsl', RW, RH), ('rsr', RW, RH), ('ctl', 86.4, 54.0)] + [(f'band[{c}].rb', RW, RH) for c in range(4)]
    # shelf packing in the spine: upper half (above the mid channel) top-down, then lower half
    dims = {}
    x, y, rowh, lo = s0, QH - G, 0, yb
    for n, w, h in sp:
        if x + w > s0 + sw:
            x = s0; y -= rowh + G + 1.08; rowh = 0
        if y - h < lo:
            x, y, rowh, lo = s0, ya + BH, 0, ya
        P[n] = (x, y - h); dims[n] = (w, h); x += w + G + .216; rowh = max(rowh, h)
    for n in P:
        if n not in dims:
            k = n.split('[')[0].split('.')[0]
            dims[n] = {'g_add': (AW, AH), 'col': (SW, SH), 'g_mult': (MW, MH), 'g_reduce': (CW, CH), 'band': (RW, RH)}[k]
    pl = {n: dict(x=round(x / .216) * .216, y=round(y / 1.08) * 1.08, w=dims[n][0], h=dims[n][1]) for n, (x, y) in P.items()}
    frozen = [n for n in pl if n.startswith(('col[', 'g_add', 'g_mult', 'g_reduce'))]
    # reserved transport regions (legal() keeps every child >= 21.6 um outside them)
    blk = [[0, 0, east + 1, ya - G - .01], [0, ya + BH + G + .01, east + 1, yb - G - .01], [east + G + .01, 0, QW, QH]]
    out.write_text(json.dumps(dict(outline_um=[QW, QH], placement=pl, blockages=blk, edge_y=None, frozen=frozen,
                                   regions=dict(spine=[s0, s0 + sw], blocks=[lx, east], east_reserve=[east + G, QW], channel_h=ch)), indent=1) + '\n')
    print('east reserve um', round(QW - east - G, 1), 'top margin', round(QH - yb - BH, 1), 'spine bottom y', round(y - rowh, 1))


if __name__ == '__main__':
    main()
