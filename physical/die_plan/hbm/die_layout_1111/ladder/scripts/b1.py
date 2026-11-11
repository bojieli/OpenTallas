#!/usr/bin/env python3
"""DIE-LAYOUT-HBM 11-11 CPL-HBM-3 Proposal B1 (COORD 12:1x adopted): the hub feeds q_b101 (NW q_b101_nw, NE q_b101)
directly with the 2176 Q bits that q_b100 today relays (procdff_71770[2197:1110],[1098:11] -> 71561 -> 71555 -> L1200).
L1228/L5028 hub->b100 lose 2176 b, L1200/L5000 b100->b101 lose 2176 b (keep header copies + 586 computed), new lanes
L1228q / L5028q hub S face -> b101 N face 2176 b, cycle-exact: natural 2 + fixed_cycles 5 = 7 (= 2 + 3 relay regs + 2).
usage: b1.py TOOLS IN.json OUT.json"""
import copy, json, sys
sys.path.insert(0, sys.argv[1] + '/tools/die_plan')
import schema as S
raw = json.load(open(sys.argv[2]))
T = raw['partition_types']
Q = 2176
OFF = 3594.24            # hub-local x - b101-local x (both quadrants, from L1221/L5021 pairs)
WINB = {'NW': (0.5, 362.2), 'NE': (363.5, 725.2)}   # b101 N face free spans (NW: L1221 at 362.7; NE: L5057 323-361, L5021 362.7); <= 6.02 b/um
PT = {p['id']: p for p in raw['ports']}
LN = {l['id']: l for l in raw['lanes']}
def bus(tn, name):
    return next(b for b in T[tn]['buses'] if b['name'] == name)
def shrink(b, w):
    b['width'] = w          # window kept: the face density drops (G0 faces)
for q, hub, b100, b101, lin, lrel in (('NW', 'q_hub_nw', 'q_b100', 'q_b101_nw', 'L1228', 'L1200'),
                                      ('NE', 'q_hub_ne', 'q_b100__physical_v1', 'q_b101', 'L5028', 'L5000')):
    # input lane hub -> b100 and relay lane b100 -> b101 shrink by Q
    for lid, (st, sb), (dt, db) in ((lin, (hub, lin + '_o'), (b100, lin + '_i')), (lrel, (b100, lrel + '_o'), (b101, lrel + '_i'))):
        p = PT[LN[lid]['ports'][0]]; w = p['width'] - Q; p['width'] = w
        shrink(bus(st, sb), w); shrink(bus(dt, db), w)
    tmpl = bus(hub, lin + '_o'); nid = lin + 'q'
    T[hub]['buses'].append(dict(copy.deepcopy(tmpl), name=nid + '_o', dir='out', width=Q, face='S', window_um=[round(WINB[q][0] + OFF, 3), round(WINB[q][1] + OFF, 3)]))
    T[b101]['buses'].append(dict(copy.deepcopy(tmpl), name=nid + '_i', dir='in', width=Q, face='N',
                                 window_um=list(WINB[q])))
    raw['ports'].append(dict(id=nid + '_0', src=dict(part=q + '_hub', bus=nid + '_o'), dst=dict(part=q + '_b101', bus=nid + '_i'),
                             width=Q, kind='data'))
    raw['lanes'].append(dict(id=nid, ports=[nid + '_0'], fixed_cycles=5,
                             note=f'DIE-LAYOUT-HBM 11-11 CPL-HBM-3 B1: {q}_hub->{q}_b101 2176 b Q direct (was relayed in {q}_b100 via {lrel}, 3 regs); fixed 5 = cycle-exact 7'))
    LN[lid] = raw['lanes'][-1]
P = S.Plan(raw)
lat = raw['latency']['lanes']
for lid in ('L1228', 'L1200', 'L5028', 'L5000', 'L1228q', 'L5028q'):
    new = P.lane_latency(lid)
    lat[lid] = dict(new, param=(lat.get(lid) or {}).get('param', 'LAT_' + lid.upper()))
    print(lid, lat[lid])
json.dump(raw, open(sys.argv[3], 'w'), indent=1)
