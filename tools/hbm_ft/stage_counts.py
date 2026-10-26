#!/usr/bin/env python3
"""FT-HBM static-schedule stage counts per die lane path (src -> dst): now (r18h5 netlist) vs the FT plan.

    stage_counts.py paths.json decimate_report_1000.json decimate_report_1200.json --out stage_counts.json

Columns per path: bits, stages_now (relay/landing rows on the deepest chain into the tail), kept_1000 / kept_1200
(decimate_plan.py: hop <= 1.0 / 1.2 mm along the CURRENT channel route, forks/merges/heads/tails kept),
route_1000 (ceil(route/1.0 mm), ideal on the current route), straight_1000 / straight_1200 (ceil(Manhattan/hop): the
lane goes straight through blocks on feedthroughs).  The compiler's link latency for a lane = its stage count
(each stage one cycle at 833 ps); only stage counts change, no functional change (FT-PLAN freeze rule)."""
import argparse, collections, json, re
ap = argparse.ArgumentParser(); ap.add_argument('paths'); ap.add_argument('d1000'); ap.add_argument('d1200'); ap.add_argument('--out', required=True)
a = ap.parse_args()
P = json.load(open(a.paths)); D1 = {p['tail']: p for p in json.load(open(a.d1000))['paths']}; D2 = {p['tail']: p for p in json.load(open(a.d1200))['paths']}
rows = []
for p in P:
    rows.append(dict(src=p['src'], dst=p['dst'], tail=p['tail'], bits=p['bits'], manh_um=p['manh_um'], route_um=p['route_um'],
                     stages_now=p['stages'], kept_1000=D1[p['tail']]['stages_kept'], kept_1200=D2[p['tail']]['stages_kept'],
                     route_1000=p['r1000'], straight_1000=p['s1000'], straight_1200=p['s1200']))
def cls(n): return re.sub(r'_?[NSEW]{1,2}\d*(_[a-z])?$', '', n or 'port/cell')
K = ('stages_now', 'kept_1000', 'kept_1200', 'route_1000', 'straight_1000', 'straight_1200')
by = collections.defaultdict(lambda: dict(paths=0, bits=0, **{k: 0 for k in K}, **{'max_' + k: 0 for k in K}))
for r in rows:
    g = by[f'{cls(r["src"])}>{cls(r["dst"])}']; g['paths'] += 1; g['bits'] += r['bits']
    for k in K: g[k] += r[k]; g['max_' + k] = max(g['max_' + k], r[k])
tot = {k: sum(r[k] for r in rows) for k in K}
json.dump(dict(schema='opentallas.hbm_ft.stage_counts.v1', case='r18h5 probe600 die.v (src d34578d6f)', totals=tot, paths=len(rows),
               by_class=dict(sorted(by.items(), key=lambda t: -t[1]['stages_now'])), rows=rows), open(a.out, 'w'), indent=0)
print(json.dumps(tot))
for k, g in list(sorted(by.items(), key=lambda t: -t[1]['max_stages_now']))[:12]:
    print(f"{k:40s} paths {g['paths']:4d} max now {g['max_stages_now']:3d} kept1.0 {g['max_kept_1000']:3d} kept1.2 {g['max_kept_1200']:3d} straight1.0 {g['max_straight_1000']:3d}")
