#!/usr/bin/env python3
"""Dataflow start placement of one BANDED MIX4 copy cluster ot_s81_engram_mixq_b (R0 everywhere: the closed leaf LEFs
declare no symmetry).

Closed-leaf pin faces: arithmetic inputs S / outputs N, so data flows S -> N.  Each band is a vertical COLUMN, 203.04 um
wide, bottom -> top: shell payload leaf shcol_b (new master: VM side on its S face, toward the cluster transport channel
under the cluster; h/kv/w/result/iv/ph on its N face) | add8 | mul4[2c] | mul4[2c+1] | chunk8 r0 r1 | chunk8 r2 + the two
top band relays (rt0, rt1: chunk sums toward the spine).  Columns c0 c1 | spine | c2 c3; an 86.4-um relay lane between
c0|c1 and c2|c3 holds the bottom band relays rb (a_gate/fr/fa/copy toward add8/shell, add8/mul4 valids toward the
control).  Two side relays rsl/rsr at the spine edges give the control's two-sided gather a second stage.  The spine (sums, norms, control, gate, central relay, shell control) sits between c1 and c2; the shell control
at its bottom, on the transport channel (edge_y = 0).  Columns are frozen; relays and spine leaves are refined by
screen.py --anneal.
"""
import json, sys
from pathlib import Path

G = 21.6
MW, MH = 181.44, 120.96; CW, CH = 90.72, 90.72; AW, AH = 181.44, 99.36; SW, SH = 164.16, 54.0
RW, RH = 43.2, 21.6
COLW = 2 * CW + G            # 203.04
LANE = RW + 2 * G            # 86.4


def column(P, c, x0):
    P[f'col[{c}].u'] = (x0 + (COLW - SW) / 2, 0.0)
    y = SH + G; P[f'g_add[{c}].leaf'] = (x0 + (COLW - AW) / 2, y)
    y += AH + G; P[f'g_mult[{2*c}].leaf'] = (x0 + (COLW - MW) / 2, y)
    y += MH + G; P[f'g_mult[{2*c+1}].leaf'] = (x0 + (COLW - MW) / 2, y)
    y += MH + G; P[f'g_reduce[0].g_chunk[{c}].leaf'] = (x0, y); P[f'g_reduce[1].g_chunk[{c}].leaf'] = (x0 + CW + G, y)
    y += CH + G; P[f'g_reduce[2].g_chunk[{c}].leaf'] = (x0, y)
    P[f'band[{c}].rt1'] = (x0 + CW + G, y); P[f'band[{c}].rt0'] = (x0 + CW + G, y + RH + 2 * G)
    return y + CH


def main():
    out = Path(sys.argv[1]); sw = float(sys.argv[2]) if len(sys.argv) > 2 else 302.4
    P = {}
    x = 0.0; column(P, 0, x)
    lane01 = x + COLW + G; x += COLW + LANE
    H = column(P, 1, x); s0 = x + COLW + G
    x = s0 + sw + G; column(P, 2, x)
    lane23 = x + COLW + G; x += COLW + LANE; column(P, 3, x)
    W = x + COLW
    for c, lx, y in ((0, lane01, 97.2), (1, lane01, 250.56), (2, lane23, 97.2), (3, lane23, 250.56)):
        P[f'band[{c}].rb'] = (lx, y)
    P['hsum'] = (s0, H - 99.36); P['ksum'] = (s0 + CW + G, H - 99.36)
    P['dsum'] = (s0, H - 99.36 - G - 99.36); P['control'] = (s0 + CW + G, H - 99.36 - G - 64.8)
    P['g_norm[0].leaf'] = (s0, 346.68); P['gate_leaf.magnitude'] = (s0 + MW + G, 346.68)
    P['g_norm[1].leaf'] = (s0, 230.04); P['relay'] = (s0 + MW + G, 230.04)
    P['gate_leaf.sigmoid'] = (s0, 98.28); P['ctl'] = (s0, 22.68)
    P['rsl'] = (s0, 300.0); P['rsr'] = (s0 + sw - RW, 300.0)
    dims = {'col': (SW, SH), 'g_add': (AW, AH), 'g_mult': (MW, MH), 'g_reduce': (CW, CH), 'band': (RW, RH), 'hsum': (CW, 99.36),
            'ksum': (CW, 99.36), 'dsum': (CW, 99.36), 'control': (CW, 64.8), 'g_norm': (MW, 95.04), 'relay': (RW, RH), 'rsl': (RW, RH), 'rsr': (RW, RH), 'ctl': (86.4, 54.0)}
    pl = {}
    for n, (x, y) in P.items():
        k = n.split('[')[0].split('.')[0]
        w, h = (64.8, 43.2) if n == 'gate_leaf.magnitude' else (MW, 110.16) if n == 'gate_leaf.sigmoid' else dims[k]
        pl[n] = dict(x=round(x / .216) * .216, y=round(y / 1.08) * 1.08, w=w, h=h)
    frozen = [n for n in pl if n.startswith(('col[', 'g_add', 'g_mult', 'g_reduce'))]
    out.write_text(json.dumps(dict(outline_um=[round(W / .216) * .216, round(H / 1.08) * 1.08 + 1.08], placement=pl, blockages=[],
                                   edge_y=0.0, frozen=frozen), indent=1) + '\n')
    print(W, H, len(pl))


if __name__ == '__main__':
    main()
