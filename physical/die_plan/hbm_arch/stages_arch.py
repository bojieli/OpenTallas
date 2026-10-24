#!/usr/bin/env python3
"""HBM-ARCH: per-class relay stages of a gen_arch plan for hgi_sim.plan_study_price_1017 (class keys of stages.json).

Class = (src partition role, dst partition role) over the plan lanes; value = bit-weighted mean lane latency in cycles
(2 boundary flops + ft stations, PLAN-TOOL formula; upper bound on the relay stages the v6_eval classes count), as
HBM-P7 stages_p5.py does for v2.  The quad tile keeps COLL engine, VM hub + banks, IDX q, SU qcore inside the HUB
partition: COLL_VM and VM_HUB = 2 (one in-partition hop each way, assumed as in stages_p5).  LG_* keep plan_b.  The
P5 SM-split adders (+1 SM_X, +1 SM_HBM, +3 SM_OUT) are added as in price_p5.sh (conservative for the P=3 SM).

    python3 stages_arch.py PLAN_DIR BASE_STAGES_JSON OUT_JSON --slot plan_b [--slot plan_c ...]
"""
import collections, json, re, sys

pdir, base_p, out_p = sys.argv[1:4]
slots = [sys.argv[i + 1] for i, x in enumerate(sys.argv) if x == '--slot']
plan = json.load(open(f'{pdir}/die_plan.json'))
lat = plan['latency']['lanes']
ports = {p['id']: p for p in plan['ports']}


def role(p):
    if p.startswith('PHY'):
        return 'PHY'
    if p in ('root',):
        return 'root'
    loc = re.sub(r'^(NW|NE|SW|SE)_', '', p)
    if re.match(r'sm\d', loc): return 'sm'
    if re.match(r'su\d', loc): return 'su'
    if re.match(r'sp', loc): return 'spine'
    if loc == 'hub': return 'hub'
    if re.match(r'b0', loc): return 'hcb'
    if re.match(r'b10', loc): return 'idx'
    if re.match(r'b11', loc): return 'sfuc'
    if loc == 'io': return 'io'
    if re.match(r'mc', loc): return 'mc'
    return 'seam'


acc = collections.defaultdict(lambda: [0.0, 0])
for ln in plan['lanes']:
    s = ports[ln['ports'][0]]['src']['part']; d = ports[ln['ports'][-1]]['dst']['part']
    w = ports[ln['ports'][0]]['width']
    rs, rd = role(s), role(d)
    same = s[:2] == d[:2]
    key = (rs, rd, 'x' if (rs == rd == 'hub' and not same) else '')
    acc[key][0] += w * lat[ln['id']]['cycles']; acc[key][1] += w


def mean(*pairs):
    t = b = 0
    for (rs, rd, x) in pairs:
        for (a, c, y), (v, n) in acc.items():
            if re.fullmatch(rs, a) and re.fullmatch(rd, c) and (x is None or x == y):
                t += v; b += n
    return round(t / b, 2) if b else None


C = dict(
    SM_HBM=mean(('spine', 'sm', None)),
    SM_X=mean(('hub', 'sm', None)),
    SM_OUT=mean(('sm', 'hub|spine', None)),
    HBM_VM=mean(('spine', 'hub', None)),
    VM_HBM=mean(('hub', 'spine', None)),
    VM_RING=mean(('hub', 'hub', 'x')),
    COLL_RING=mean(('hub', 'hub', 'x')),
    COLL_EP=mean(('hub', 'io', None), ('io', 'hub', None)),
    HC_CORE=mean(('hcb', 'hub', None), ('hub', 'hcb', None)),
    HC_ENG=mean(('hub', 'root', None), ('root', 'hub', None)),
    SFU_CORE=mean(('sfuc|su', 'hub|sfuc', None), ('hub', 'sfuc', None)),
    SU_CORE=mean(('su', 'hub', None), ('hub', 'su', None)),
    KV_DESC=mean(('spine', 'hub', None), ('hub', 'spine', None)),
)
base = json.load(open(base_p))
st = dict(base['plan_b'])
for k, v in C.items():
    if v is not None:
        st[k] = v
st['VM_HUB'] = 2.0
st['COLL_VM'] = 2.0
for k, dd in (('SM_X', 1), ('SM_HBM', 1), ('SM_OUT', 3)):
    st[k] = round(st[k] + dd, 2)
for sl in slots:
    base[sl] = st
json.dump(base, open(out_p, 'w'), indent=1)
print(json.dumps({k: st[k] for k in sorted(st)}))
