#!/usr/bin/env python3
"""HBM-R15: move internal_stations registers that sit inside a hard core (after outline growth) to the nearest free 4.32
lattice point 2.16 um clear of every hard core of the type (inside the type outline). Register COUNT unchanged (no cycle
change). Reports chains whose max hop then exceeds 405 (relax_route follows). Also puts EP clk on its centre entry.
usage: incore_restation.py PLANDIR"""
import json, sys, math
from pathlib import Path
d = Path(sys.argv[1]); p = json.loads((d/'die_plan.json').read_text())
G, CL = 4.32, 2.16
md = lambda a, b: abs(a[0]-b[0])+abs(a[1]-b[1])
rep = dict(moved=0, chains=0, over405=[], maxdisp=0.0)
for tn, t in p['partition_types'].items():
    hc = [(c['origin_um'][0], c['origin_um'][1], c['origin_um'][0]+c['outline_um'][0], c['origin_um'][1]+c['outline_um'][1]) for c in t.get('hard_cores', [])]
    if not hc: continue
    W, H = t['outline_um']
    inside = lambda x, y, m=0: any(a-m < x < c+m and b-m < y < e+m for a, b, c, e in hc)
    for e in t.get('internal_stations', []) or []:
        regs = e.get('regs_um') or []; ch = False
        for i, r in enumerate(regs):
            if not inside(r[0], r[1]): continue
            best = None
            for rad in range(1, 400):
                cands = []
                for dx in range(-rad, rad+1):
                    for dy in (-rad, rad) if abs(dx) != rad else range(-rad, rad+1):
                        x = (round(r[0]/G)+dx)*G; y = (round(r[1]/G)+dy)*G
                        if 0 < x < W and 0 < y < H and not inside(x, y, CL): cands.append((math.hypot(x-r[0], y-r[1]), x, y))
                if cands: best = min(cands); break
            assert best, (tn, e['conn'], r)
            rep['maxdisp'] = max(rep['maxdisp'], round(best[0], 2))
            regs[i] = [round(best[1], 3), round(best[2], 3)]; rep['moved'] += 1; ch = True
        if ch:
            rep['chains'] += 1
            pts = [e['from_um']] + regs + [e['to_um']]
            w = max(md(a, b) for a, b in zip(pts, pts[1:]))
            if w > 405: rep['over405'].append((tn, e['conn'], round(w, 1)))
(d/'die_plan.json').write_text(json.dumps(p, indent=1)+'\n')
epf = d/'cores/hfd_ep_static__241.92x397.44__r15_wesplit.json'
pins = json.loads(epf.read_text())
for q in pins:
    if q['name'] == 'clk': q.update(layer='M5', x=120.984, y=198.744)
epf.write_text(json.dumps(pins, indent=1)+'\n')
(d/'incore_restation_report.json').write_text(json.dumps(rep, indent=1)+'\n')
print(rep['moved'], rep['chains'], len(rep['over405']), rep['maxdisp'])
