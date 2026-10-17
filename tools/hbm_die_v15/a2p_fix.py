#!/usr/bin/env python3
"""A2P plan fixes (coordinator 10-16 19:30): COLL_EP -> ep rows beside COLL (just under / over hc_eng in the E column),
lk SerDes tiles against the E die edge next to their ep row; optional PHY/PC shift toward the VM hub (HBM_VM).
    a2p_fix.py PLAN_DIR [--phy-shift UM]      (rewrites compact.P.json in place)"""
import argparse, json
from pathlib import Path
GAP, EDGE = 100.0, 42.4
ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('--phy-shift', type=float, default=0.0)
a = ap.parse_args(); d = Path(a.plan)
P = json.loads((d / 'compact.P.json').read_text()); W, H = json.loads((d / 'compact.metrics.json').read_text())['die_um']
e = P['hc_eng']; c0 = e['x']; cr = W - EDGE
for side, sgn in (('S', -1), ('N', 1)):
    eps = sorted(k for k in P if k.startswith(f'ep_{side}')); lks = sorted(k for k in P if k.startswith(f'lk_{side}'))
    ew, eh = P[eps[0]]['w'], P[eps[0]]['h']; lw, lh = P[lks[0]]['w'], P[lks[0]]['h']
    ye = e['y'] - GAP - eh if sgn < 0 else e['y'] + e['h'] + GAP
    for k, n in enumerate(eps):
        P[n].update(x=round(cr - (k + 1) * ew - k * GAP / 2, 3), y=round(ye, 3))
    yl = ye - GAP - lh if sgn < 0 else ye + eh + GAP
    for k, n in enumerate(lks):
        P[n].update(x=round(cr - (k + 1) * lw - k * GAP, 3), y=round(yl, 3))
if a.phy_shift:
    for k in P:
        if k.startswith(('phy_', 'pc_')):
            P[k]['x'] = round(P[k]['x'] + a.phy_shift, 3)
(d / 'compact.P.json').write_text(json.dumps(P, indent=1))
