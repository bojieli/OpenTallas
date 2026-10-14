#!/usr/bin/env python3
"""Qwen tp8b die plan for the per-pair hop check (tools/hier_contract/pinreg_pairs.py plan): build the die as
relay_data_run.py does and dump every die-level bus hop driver -> load with the generator's own pin-to-pin measure
(bounding box of the two ports' pin centroids, instance orientation applied) in the S81 plan format.

usage (repo root): python3 tools/qwen_tp8/pairs_plan_dump.py OUT.json.gz
plan: insts [name, master, x, y, w, h, orient, kind, region], hops [bus, cls, bits, drv, dport, load, lport, [xa, ya],
[xb, yb], um, um], clock_nets {bus: [[inst, port], ...]} (class clock_trunk: the die tree's leaf nets, no driver)."""
import gzip, json, sys, time
sys.path.insert(0, 'tools'); sys.path.insert(0, 'results/arch/qwen_tp8_1012')
import die_top_lint as D
import qwen_rom_fulldie_b3r2 as G

t = time.time()
D.QWEN_RECIPE = 'tp8b'; D._QW.clear(); D.QSRC = None
v, m = D.load_qwen()[:2]
pos = G._pin_pos(v, m)
hops, clock = [], {}
for bid, cl, bits, eps in m['buses']:
    eps = [(e[0], e[1].lstrip('*')) for e in eps]
    if cl == 'clock_trunk':
        clock[bid] = [list(e) for e in eps]
        continue
    if len(eps) < 2:
        continue
    d = eps[0]
    pa = pos(*d)
    for e in eps[1:]:
        pb = pos(*e)
        L = round(abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]), 1)
        hops.append([bid, cl, bits, d[0], d[1], e[0], e[1], [round(q, 2) for q in pa], [round(q, 2) for q in pb], L, L])
r = m.get('r21_relays') or {}
with gzip.open(sys.argv[1], 'wt') as f:
    json.dump(dict(die=list(m['die']), recipe='tp8b', measure='pin centroid to pin centroid (Manhattan) of the two ports, generator pin model',
                   insts=[[i.name, getattr(i, 'master', ''), round(i.x, 3), round(i.y, 3), round(i.w, 3), round(i.h, 3), i.orient,
                           getattr(i, 'kind', ''), ''] for i in m['insts']],
                   hops=hops, clock_nets=clock, stage_of=m.get('r21_stage_of'),
                   relays={k: r.get(k) for k in ('relays', 'max_pin_to_pin_um', 'reach_um', 'unrepaired', 'over_reach', 'pair_check')}), f)
print(json.dumps(dict(insts=len(m['insts']), hops=len(hops), clock_nets=len(clock), build_s=round(time.time() - t))))
