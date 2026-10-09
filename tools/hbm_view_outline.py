#!/usr/bin/env python3
"""safe-hbm (2026-10-08, reviewer decision R-Q3): re-outline a die view's ports (tools/hbm_die_views.py ports output) to
a smaller block W x H, every pin kept on its face and in its order, at its original pitch inside a port group (gaps between groups
closed to <= 2 um), each face's pins centred on the new face.  Rewrites <dir>/<master>/ports.json and io_place.tcl in place.  The die floorplan must adopt the new slot
(the r25 slot of hfd_quant is 1,399.656 x 358.536 um at 4.6 % std-cell utilisation; the variant sizes it for ~50 %).
    hbm_view_outline.py <ports dir> <master> <W um> <H um>"""
import json
import sys
from pathlib import Path

d, master, W, H = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
pj = d / master / 'ports.json'
P = json.loads(pj.read_text())
w0, h0 = P['w_um'], P['h_um']


def face_of(r):
    _, _, x0, y0, x1, y1 = r
    dist = dict(S=y0, N=h0 - y1, W=x0, E=w0 - x1)
    return min(dist, key=dist.get)


faces = {}
for p, v in P['ports'].items():
    for r in v.get('pins', []):
        faces.setdefault(face_of(r), []).append((p, r))
new = {}
for f, lst in faces.items():
    horiz = f in ('S', 'N')
    key = (lambda pr: pr[1][2]) if horiz else (lambda pr: pr[1][3])
    lst.sort(key=key)
    # keep the pitch inside each port group; gaps between groups (and stray pins such as ck / rst) close to <= GAP um
    GAP = 2.016
    pos, prev, acc = [], None, 0.0
    for p, r in lst:
        k = key((p, r))
        if prev is not None:
            acc += min(k - prev, GAP)
        pos.append(acc)
        prev = k
    span0 = pos[-1]
    L = W if horiz else H
    assert span0 <= L - 4.0 or len(lst) == 1, (f'{f} face pins span {span0:.3f} um > new face {L} um')
    start = round(((L - span0) / 2) / 0.048) * 0.048
    for (p, r), a in zip(lst, pos):
        off = start + a - key((p, r))
        off = round(off / 0.048) * 0.048
        n, lay, x0, y0, x1, y1 = r
        pw, ph = x1 - x0, y1 - y0
        if horiz:
            x0n = round(x0 + off, 4)
            y0n = 0.0 if f == 'S' else round(H - ph, 4)
        else:
            y0n = round(y0 + off, 4)
            x0n = 0.0 if f == 'W' else round(W - pw, 4)
        new[n] = [n, lay, x0n, y0n, round(x0n + pw, 4), round(y0n + ph, 4)]
for p, v in P['ports'].items():
    v['pins'] = [new[r[0]] for r in v.get('pins', [])]
P['w_um'], P['h_um'] = W, H
P['note'] = (P.get('note', '') + f' | safe-hbm R-Q3 outline variant {W} x {H} (was {w0} x {h0}): pins kept on their '
             'faces, order and in-group pitch (group gaps closed to <= 2 um), centred; the die floorplan must adopt this slot')
pj.write_text(json.dumps(P, indent=1) + '\n')
io = d / master / 'io_place.tcl'
lines = [f'# {master}: R-Q3 outline variant {W} x {H} (tools/hbm_view_outline.py from the r25 ports)']
for p, v in sorted(P['ports'].items()):
    for n, lay, x0, y0, x1, y1 in v['pins']:
        lines.append(f'place_pin -pin_name {{{n}}} -layer {lay} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                     f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
io.write_text('\n'.join(lines) + '\n')
print(json.dumps({f: len(l) for f, l in faces.items()}), W, H)
