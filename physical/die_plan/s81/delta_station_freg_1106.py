#!/usr/bin/env python3
"""Private S81 station input-capture event, on the adopted ft3 geometry A plan.

No CA straps/control phases change. The three data+epoch crossings each gain
one cycle. This replay emits candidate artifacts; it does not overwrite plans.
"""
import argparse, copy, json
from pathlib import Path

SELECTED = {'slice_station__t41': ['ft2_i'],
            'slice_station__t51': ['ft2_i', 'ft3_i']}
RECTS = {'ft2_i': [17.28, 1211.76, 117.72, 1221.48],
         'ft3_i': [119.04, 1211.76, 228.828, 1221.48]}

def apply(plan, sidecar):
    p, s = copy.deepcopy(plan), copy.deepcopy(sidecar)
    assert s['added_cycles_per_crossing'] == 3
    assert p['partition_types']['slice_station__t51']['clock']['landing_contract']['bands']['ft3_i']['rect_um'] == [302.4,1144.8,388.8,1209.228]
    parts = {x['name']: x['type'] for x in p['partitions']}
    for tn, buses in SELECTED.items():
        c = p['partition_types'][tn]['clock']
        assert 'landing_input_freg' not in c
        c['landing_input_freg'] = buses
        for bus in buses:
            band = c['landing_contract']['bands'][bus]
            r, m = RECTS[bus], band['rect_um']
            hop = max(abs(x-X)+abs(y-Y) for x in r[::2] for y in r[1::2] for X in m[::2] for Y in m[1::2])
            assert hop <= 402.84
            band['freg_rect_um'] = r
    ports = [x for x in p['ports'] if x['dst']['bus'] in SELECTED.get(parts[x['dst']['part']], [])]
    assert len(ports) == 3
    rows = {x['port']: x for x in s['ports']}
    delta = {}
    for x in ports:
        row = rows[x['id']]
        assert row['added_cycles'] == 3
        row['added_cycles'] = 4
        delta[row['lane']] = delta.get(row['lane'], 0)+1
    for lane, n in delta.items():
        for key in ('clock_landing', 'cycles', 'natural'):
            p['latency']['lanes'][lane][key] += n
    return p, s, {'ports': [x['id'] for x in ports], 'lane_cycle_delta': delta,
                  'payload_bits': 515, 'own_control_added_cycles': 0,
                  'note': 'data+epoch only; separate ring ready/fault unchanged'}

if __name__ == '__main__':
    a=argparse.ArgumentParser();a.add_argument('plan',type=Path);a.add_argument('sidecar',type=Path);a.add_argument('--out',type=Path,required=True)
    args=a.parse_args();p,s,e=apply(json.loads(args.plan.read_text()),json.loads(args.sidecar.read_text()))
    args.out.mkdir(parents=True,exist_ok=True)
    for name,value in [('plan.json',p),('sidecar.json',s),('event.json',e)]:
        (args.out/name).write_text(json.dumps(value,indent=2)+'\n')
