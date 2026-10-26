#!/usr/bin/env python3
"""P5: stages_p4.py + the direct x path (COORD HBM PRICE RULING 14:44 (1)): when the xq engines sit in the VM
slice (OT_HBM_XDIRECT), SM_X = the VM -> SM xq/xl lanes (one leg) instead of SM_X1 (vm -> svc) + SM_X2 (svc -> sm).
Pads: the plan's own land_pad notes (word landing) are priced as they stand; --nopad drops them (lower bound).

Per-class plan stages of HBM plan v2 for hgi_sim.plan_study_price_1017 (same class keys as stages.json plan_b).

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
C['SM_XD'] = mean(r'vm|su2', r'sm\d[a-d]', r'xq|xl')   # p1 egress sits in SU2 (SM 2/3)
_p1 = mean(r'vm', r'su2', r'xq')                            # its bfq -> eg leg (vm -> su2), half the SMs
if C['SM_XD'][0] is not None and _p1[0]:
    C['SM_XD'] = (C['SM_XD'][0] + 0.5 * (_p1[0] - 1), C['SM_XD'][1])
if C['SM_XD'][1] and C['SM_XD'][1] > (C['SM_X1'][1] or 0):
    sm_x = C['SM_XD'][0]                       # P5 direct x path: one VM -> SM leg
    # XLAND=xw: the leg ends on quarter a; the SM relays a -> b -> c (smq lanes, one direct hop each); chained lanes
    # share the junction flop (-1 each)
    ab = mean(r'sm\d[a]', r'sm\d[b]', r'smq'); bc = mean(r'sm\d[b]', r'sm\d[c]', r'smq')
    xd_dst = collections.Counter()
    for ln in plan['lanes']:
        m = re.match(r'^(L\d+)s\d+([a-d])_\d+$', ln['id'])
        lm = m and mem.get(m.group(1) + m.group(2))
        if lm and any(n.split('.')[1].startswith('xw_') for n in lm['nets']):
            xd_dst[ports[ln['ports'][-1]]['dst']['part'][-1]] += 1
    if xd_dst and max(xd_dst, key=xd_dst.get) == 'a' and ab[0] and bc[0]:
        sm_x += (ab[0] - 1) + (bc[0] - 1)
        detail['SM_X_relay'] = dict(ab=ab[0], bc=bc[0], xw_lane_dst_quarters=dict(xd_dst))
else:
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
