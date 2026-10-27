#!/usr/bin/env python3
"""HBM-MU-QUAD-3 delta (F3): (1) root TKM corridor clock branch buffers centred on their tap column (plan geometry: the
buffer sat at the corridor E end, 475-um legs > 405 reach; the centred site is in the same corridor, legs = the two
equal vertical legs) -- plan-computed placement before any build, not a post-measurement trim; (2) die latency table
updated to the plan's lane cycles for the lanes that gained pushdown stations in the spanning growth (the added cycles
are priced, listed in delta_report.json).  Usage: fix3.py PLAN_DIR G0_REPORT"""
import json, sys, re, pathlib, hashlib
pd = pathlib.Path(sys.argv[1]); P = json.load(open(pd / 'die_plan.json')); g0 = json.load(open(sys.argv[2]))
rep = json.load(open(pd / 'delta_report.json'))
ck = P['partition_types']['root']['clock']; taps = {t['name']: t for t in ck['taps']}
hc = [(h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1])
      for h in P['partition_types']['root']['hard_cores']]
bb = []
for b in ck.get('branch_buffers', []):
    if max(b.get('legs_um', [0])) <= 405:
        continue
    xs = {round(taps[d]['xy'][0], 3) for d in b['drives']}
    if len(xs) != 1:
        continue
    x = xs.pop(); y = b['xy'][1]
    if any(a < x < c and e < y < f for a, e, c, f in hc):
        continue
    dx = x - b['xy'][0]
    b['xy'] = [x, y]; b['cell_ll_um'] = [round(b['cell_ll_um'][0] + dx, 3), b['cell_ll_um'][1]]
    b['legs_um'] = [round(abs(taps[d]['xy'][0] - x) + abs(taps[d]['xy'][1] - y), 3) for d in b['drives']]
    b['note'] = b.get('note', '') + ' | HBM-MU-QUAD-3: centred on the tap column (plan geometry, legs <= reach)'
    bb.append(dict(name=b['name'], xy=b['xy'], legs_um=b['legs_um']))
lat = []
for f in g0['findings']:
    m = re.match(r'lane (\S+): table says (\d+) cycles, plan gives (\d+)', f.get('msg', ''))
    if f['level'] == 'ERROR' and m:
        ln, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        e = P['latency']['lanes'][ln]; d = b - a
        e['cycles'] = b; e['natural'] = e.get('natural', a) + d; e['stations'] = e.get('stations', 0) + d
        lat.append(dict(lane=ln, was=a, now=b, added=d))
rep['F3_branch_buffers'] = bb; rep['F3_latency'] = lat
s = json.dumps(P, indent=1) + '\n'
(pd / 'die_plan.json').write_text(s); (pd / 'die_plan.sha256').write_text(hashlib.sha256(s.encode()).hexdigest() + '  die_plan.json\n')
(pd / 'delta_report.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps(dict(sha=hashlib.sha256(s.encode()).hexdigest()[:12], bb=bb, lat=lat)))
