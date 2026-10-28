#!/usr/bin/env python3
"""PG-ACTIVITY-3 coupon: replace a window kit's C4 bumps by an EDGE-FIT lattice.
Rows/columns run from margin to (die - margin) with the smallest integer interval count whose pitch is >= 150 um,
so both die edges get a bump row/column at `margin` (pad 70 um; centre margin default 60 um, as BUMP-SURVEY --edge-margin 60).
Checkerboard VDD/VSS by (i+j) parity, same as die_trial.bump_grid. Only ot_pad lines are rewritten."""
import json, math, re, sys
kit, W, H = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
margin = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0
def axis(L):
    n = math.floor((L - 2 * margin) / 150.0)          # intervals; pitch >= 150
    p = (L - 2 * margin) / n
    return [margin + p * k for k in range(n + 1)], p
xs, px = axis(W); ys, py = axis(H)
m = json.load(open(kit + '/irwin.json')); x0, y0, x1, y1 = m['window_um']
lines = []; k = 0
for i, x in enumerate(xs):
    for j, y in enumerate(ys):
        if x0 <= x <= x1 and y0 <= y <= y1:
            lines.append(f"ot_pad {'VDD' if (i + j) % 2 else 'VSS'} {k} {x - x0:.3f} {y - y0:.3f}"); k += 1
t = open(kit + '/psm/bumps.tcl').read()
head = t[:t.index('\not_pad ') + 1]; tail = t[t.rindex('\not_pad '):]; tail = tail[tail.index('\n', 1):]
open(kit + '/psm/bumps.tcl', 'w').write(head + '\n'.join(lines) + tail)
m.update(bumps=k, bumps_vdd=sum('VDD' in l for l in lines), bump_lattice=dict(kind='edge-fit', margin_um=margin, pitch_x_um=px, pitch_y_um=py, nx=len(xs), ny=len(ys)))
json.dump(m, open(kit + '/irwin.json', 'w'), indent=2)
print(json.dumps(dict(bumps=k, pitch_x=round(px, 4), pitch_y=round(py, 4), first_rows=[round(y - y0, 2) for y in ys if y0 <= y <= y1][:3])))
