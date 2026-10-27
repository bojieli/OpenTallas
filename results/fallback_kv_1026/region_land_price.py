#!/usr/bin/env python3
"""FALLBACK-KV 10-26: price the 8-region landed fallback on the Qwen token path.

Input: the die clock proof's landed_crossings.json (die_clock_mesh build, region spec = dataflow cuts) and the
die plan. Every landed port adds K cycles to its lane (one landing per crossed region seam). The lane delta table
is mapped onto lat_v39r lanes by lane endpoint (src part.bus, dst part.bus) and priced with the unchanged
kv_v39r_price.py lane-class model (same tool the FALLBACK-LAND all-seam price used).

    region_land_price.py PLAN LANDED_CROSSINGS LAT_V39R K OUT_DELTA.json
"""
import json, sys
from collections import defaultdict
plan, lcf, latf, K, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
P = json.load(open(plan)); LC = json.load(open(lcf)); LAT = json.load(open(latf))
ports = {p['id']: p for p in P['ports']}
cross = defaultdict(int)
for q in LC['ports']:
    cross[q['lane']] += 1
ends = {}
for l in P['lanes']:
    a, b = ports[l['ports'][0]], ports[l['ports'][-1]]
    ends[l['id']] = (a['src']['part'] + '.' + a['src']['bus'], b['dst']['part'] + '.' + b['dst']['bus'])
byend = defaultdict(list)
for n, v in LAT['lanes'].items():
    byend[(v['src']['part'] + '.' + v['src']['bus'], v['dst']['part'] + '.' + v['dst']['bus'])].append(n)
L, miss, mapped = [], [], 0
for n, v in LAT['lanes'].items():
    L.append(dict(lane=n, src=v['src']['part'] + '.' + v['src']['bus'], dst=v['dst']['part'] + '.' + v['dst']['bus'],
                  width=v['width'], delta=0))
idx = {d['lane']: d for d in L}
for lid, c in cross.items():
    e = ends.get(lid)
    hits = byend.get(e, []) if e else []
    if not hits:
        miss.append(lid); continue
    for h in hits:
        idx[h]['delta'] += K * c
    mapped += 1
json.dump(dict(note=f'8-region landed fallback: +{K} per landed region crossing (landed_crossings.json)',
               lanes=L, mapped_lanes=mapped, unmapped_landed_lanes=miss,
               landed_ports=len(LC['ports']), landed_bits=LC['bits']), open(out, 'w'), indent=1)
print(f'K={K} landed lanes {len(cross)} mapped {mapped} unmapped {len(miss)}; lanes with delta',
      sum(1 for d in L if d['delta']), 'max delta', max(d['delta'] for d in L))
