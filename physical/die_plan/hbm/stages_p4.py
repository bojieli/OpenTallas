#!/usr/bin/env python3
"""Per-class plan stages of HBM plan v2 for hgi_sim.plan_study_price_1017 (same class keys as stages.json plan_b).

Class = (src partition role, dst partition role) pattern over the v2 lanes; value = bit-weighted mean of the lane
latency in cycles (2 boundary flops + stations, the PLAN-TOOL formula), so it is an upper bound on the relay stages
the v6_eval classes count.  Two-leg paths (VM -> svc xq/xc -> SM) add both legs.  VM_HUB is internal to the VM slice
partition in v2 (hub and its 8 banks in one 2.3 x 2.9 mm partition): 2 stages assumed (one in-partition hop each
way, to be measured).  LG_* (fixed-return engine faces) keep the plan_b values: the LG pairs are the same
neighbour faces in v2.
"""
import argparse, collections, gzip, json, re

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--base', required=True, help='stages.json (hbm_plan_study_1017)')
ap.add_argument('--nopad', action='store_true')
ap.add_argument('--name', default='stages_v2.json')
a = ap.parse_args()
NOPAD = a.nopad
plan = json.load(open(f'{a.out}/die_plan.json'))
mem = json.load(gzip.open(f'{a.out}/lane_members.json.gz'))
ports = {p['id']: p for p in plan['ports']}
lat = plan['latency']['lanes']
PAD = {l['id']: int(re.search(r'land_pad (\d+)', l['note']).group(1)) for l in plan['lanes'] if 'land_pad' in l.get('note', '')}
role = lambda p: 'C0' if p == 'C0' else 'PHY' if p.startswith('PHY') else re.sub(r'^(NW|NE|SW|SE)_', '', p)
pair = collections.defaultdict(lambda: [0.0, 0])          # (src role, dst role, net-family) -> [sum bits*cyc, bits]
for ln in plan['lanes']:
    m = re.match(r'^(L\d+)s\d+([a-d])_\d+$', ln['id'])
    if not m:
        continue
    lm = mem.get(m.group(1) + m.group(2))
    if not lm:
        continue
    s, d = ports[ln['ports'][0]]['src']['part'], ports[ln['ports'][-1]]['dst']['part']
    w = ports[ln['ports'][0]]['width']
    fam = ' '.join(sorted({re.sub(r'(NW|NE|SW|SE)\d*', 'Q', n.split('.')[0]) for n in lm['nets']}))
    for key in ((role(s), role(d), fam), (role(s), role(d), '*')):
        pair[key][0] += w * (lat[ln['id']]['cycles'] - (PAD.get(ln['id'], 0) if NOPAD else 0)); pair[key][1] += w


def mean(sp, dp, famre=None):
    t = b = 0
    for (s, d, f), (x, y) in pair.items():
        if f == '*' and famre is None or famre is not None and f != '*' and re.search(famre, f):
            if re.fullmatch(sp, s) and re.fullmatch(dp, d):
                t += x; b += y
    return (round(t / b, 2), b) if b else (None, 0)


C = {
    'SM_HBM': mean(r'svc\d', r'sm\d[a-d]', r'ctl|svg|cp_svg|xc'),
    'SM_X1': mean(r'vm', r'svc\d', r'xq|xl'),
    'SM_X2': mean(r'svc\d', r'sm\d[a-d]', r'xq|xc'),
    'SM_OUT': mean(r'sm\d[a-d]', r'vm|svc\d'),
    'HBM_VM': mean(r'svc\d', r'vm'),
    'VM_HBM': mean(r'vm', r'svc\d'),
    'VM_RING': mean(r'vm', r'vm'),
    'COLL_VM': (lambda x, y: ((x[0] + y[0]) / 2 if x[0] and y[0] else x[0] or y[0], x[1] + y[1]))(mean(r'rc4', r'vm'), mean(r'vm', r'rc4')),
    'COLL_EP': (lambda x, y: ((x[0] + y[0]) / 2 if x[0] and y[0] else x[0] or y[0], x[1] + y[1]))(mean(r'rc4', r'io'), mean(r'io', r'rc4')),
    'COLL_RING': mean(r'rc4', r'rc4'),
    'HC_CORE': (lambda x, y: ((x[0] + y[0]) / 2 if x[0] and y[0] else x[0] or y[0], x[1] + y[1]))(mean(r'hc\d', r'hcq'), mean(r'hcq', r'hc\d')),
    'HC_ENG': (lambda x, y: ((x[0] + y[0]) / 2 if x[0] and y[0] else x[0] or y[0], x[1] + y[1]))(mean(r'hcq|hc\d', r'C0'), mean(r'C0', r'hcq|hc\d')),
    'SFU_CORE': mean(r'sfuc|vm', r'sfuc|vm'),
    'SU_CORE': mean(r'su\d|vm', r'su\d|vm'),
    'KV_DESC': mean(r'svc\d|vm', r'svc\d|vm'),
}
base = json.load(open(a.base))['plan_b']
st = dict(base)
detail = {}
for k, (v, b) in C.items():
    detail[k] = dict(cycles=v, bits=b)
sm_x = (C['SM_X1'][0] or 0) + (C['SM_X2'][0] or 0)
for k in ('SM_HBM', 'SM_OUT', 'HBM_VM', 'VM_HBM', 'VM_RING', 'COLL_VM', 'COLL_EP', 'COLL_RING', 'HC_CORE', 'HC_ENG',
          'SFU_CORE', 'SU_CORE', 'KV_DESC'):
    if C[k][0] is not None:
        st[k] = C[k][0]
st['SM_X'] = round(sm_x, 2)
st['VM_HUB'] = 2.0
res = dict(plan_v2=st, plan_b=base, detail=detail, rule=__doc__)
json.dump(res, open(f'{a.out}/{a.name}', 'w'), indent=1)
print(json.dumps({k: (base.get(k), st[k]) for k in st}, indent=0))
