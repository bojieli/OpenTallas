#!/usr/bin/env python3
"""HBM-ARCH: per-SM-row HBM path latency + bit-mm (COORD review item 4).  Leg 1 PHY <-> hub (controllers ctl / vmks /
svg sit in the hub), leg 2 hub (+ spine cp_svg / xc) <-> SM.  Cycles = lane latency (boundary flops + stations);
bit-mm = width x routed length (checker lane geometry).  python3 hbm_rows.py PLAN_DIR"""
import collections, json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'tools', 'die_plan'))
import check as CK, schema as S
d = sys.argv[1]
raw = json.load(open(f'{d}/die_plan.json')); P = S.Plan(raw)
lat = raw['latency']['lanes']; ports = {p['id']: p for p in raw['ports']}
part_type = {p['name']:p['type'] for p in raw['partitions']}
internal_bus = {}
for tn, typ in raw['partition_types'].items():
    for entry in typ.get('internal_stations', []):
        key = str(entry.get('conn', ''))
        if key.startswith('bus:'):
            k=(tn,key[4:]);internal_bus[k]=max(internal_bus.get(k,0),len(entry['regs_um']))
acc = collections.defaultdict(lambda: [0.0, 0.0, 0, 0])     # key -> [sum w*cyc, sum w*mm, bits, max cyc]
for ln in raw['lanes']:
    s = ports[ln['ports'][0]]['src']['part']; t = ports[ln['ports'][-1]]['dst']['part']; w = ports[ln['ports'][0]]['width']
    if not s.startswith('NW_') and not t.startswith('NW_'):
        continue                                     # NE = mirror
    pts, regs, xs = CK.lane_geometry(P, ln['id'])
    L = CK.plen(pts) / 1000.0
    def r(n):
        m = re.match(r'NW_sm(\d)', n)
        return None if not m else ('near' if m.group(1) in '01' else 'far')
    key = None
    if s == 'PHY_N' and t == 'NW_hub': key = 'PHY->hub'
    elif s == 'NW_hub' and t == 'PHY_N': key = 'hub->PHY'
    elif r(t) and re.match(r'NW_(hub|sp)', s): key = f'svc->SM {r(t)}'
    elif r(s) and re.match(r'NW_(hub|sp)', t): key = f'SM->svc {r(s)}'
    if key:
        sb=ports[ln['ports'][0]]['src']['bus'];db=ports[ln['ports'][-1]]['dst']['bus']
        c = lat[ln['id']]['cycles']+internal_bus.get((part_type[s],sb),0)+internal_bus.get((part_type[t],db),0); a = acc[key]
        a[0] += w * c; a[1] += w * L; a[2] += w; a[3] = max(a[3], c)
out = {k: dict(bits=v[2], mean_cycles=round(v[0] / v[2], 2), max_cycles=v[3], bit_mm=round(v[1]), mm_per_bit=round(v[1] / v[2], 2))
       for k, v in sorted(acc.items())}
for row in ('near', 'far'):
    out[f'HBM read path {row} (PHY->hub->SM, cycles)'] = round(out['PHY->hub']['mean_cycles'] + out[f'svc->SM {row}']['mean_cycles'] - 1, 2)
json.dump(out, open(f'{d}/hbm_rows.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
