#!/usr/bin/env python3
"""d4f r4 quarter-core layout (H-DIE 10-17): when the quadrant widens (--sm-pair-gap) the band slack goes WEST of the core,
so the core stays next to its hub:
  coll_<q>  = COLL hard_v7 cluster (1080 x 880 SW q3 / 1080 x 790 q2), E edge 100 um W of the quadrant HC client hc_<q>,
              band-side edge unchanged (S-type quadrants grow away from the band edge = up, NW grows down)
  tkm_SW    = TKM sub-cluster 1740 x 1740 on coll_SW's band-interior face across 100 um, E-aligned with coll_SW
  cij_<q>   = COLL inject/IDX join on coll's W face (centred);  sucx_<q> = SU cross-port W of cij on coll's band-edge row
  sucore_<q>, dbk_<q> move east by the same shift (dbk is re-homed by d4f_fit_slots.py next to the core)
      d4f_core_shift.py PLAN_DIR"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); P = json.loads((d / 'compact.P.json').read_text())
WH = dict(SW=(1080.0, 880.0), SE=(1080.0, 790.0), NE=(1080.0, 790.0), NW=(1080.0, 790.0))
C = 21.6
for q, (w, h) in WH.items():
    c = P[f'coll_{q}']; hc = P[f'hc_{q}']
    x1 = hc['x'] - 100.0; dx = (x1 - w) - c['x']
    down = q == 'NW'                                # NW band is mirrored: COLL sits at the band top, grows down
    y = c['y'] + c['h'] - h if down else c['y']
    for k in (f'sucore_{q}', f'dbk_{q}'):
        if k in P:
            P[k]['x'] = round(P[k]['x'] + dx, 3)
    P[f'coll_{q}'] = dict(c, x=round(x1 - w, 3), y=round(y, 3), w=w, h=h)
    cj = P[f'cij_{q}']; P[f'cij_{q}'] = dict(cj, x=round(x1 - w - C - cj['w'], 3), y=round(y + (h - cj['h']) / 2, 3))
    sx = P[f'sucx_{q}']
    P[f'sucx_{q}'] = dict(sx, x=round(x1 - w - C - cj['w'] - C - sx['w'], 3), y=round((y + h - sx['h']) if down else y, 3))
    sx = P[f'sucx_{q}']
    # DMA back (+ wb_kport region 800 x 560, d4f_fit_slots.py) W of sucx on the band-edge row
    db = P[f'dbk_{q}']; P[f'dbk_{q}'] = dict(db, x=round(sx['x'] - C - 800.0, 3), y=round((y + h - 560.0) if down else y, 3), w=800.0, h=560.0)
    if q == 'SW':
        P['tkm_SW'] = dict(x=round(x1 - 1740.0, 3), y=round(y + h + 100.0, 3), w=1740.0, h=1740.0, orient='R0')
        sc = P['sucore_SW']; P['sucore_SW'] = dict(sc, x=round(min(sc['x'], P['tkm_SW']['x'] - C - sc['w']), 3))
    print(q, 'core shift', round(dx, 1))
(d / 'compact.P.json').write_text(json.dumps(P, indent=1))
