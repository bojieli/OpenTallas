#!/usr/bin/env python3
"""SU overflow homes (coordinator decision 02:00 10-16, H-SU request): one ~0.55 mm2 home per quadrant for 6 heavy lanes
(302.4 um square each, 3 x 2 grid with 21.6 um channels -> 950.4 x 626.4 um), in the outer-corner void beside the PHY
(x < PHY, below/above the first SM row) -- the void nearest the G0/G1 port groups (VIS-HBM D2).  The route to the band
uses the 120-um die-edge margin column (free full height) for relays, then the band.  Reports Manhattan length along that
route and relay stages at <= 500 um per hop (ceil(d/500) - 1) to G0/G1 VM bank pairs, the SU slices, the reducer (qcore)
and the VM hub.  CANDIDATE: H-SU measures the e2e cost before adoption."""
import json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
P = json.loads((ROOT / 'results/arch/hbm_die_v15/compact660_v5/compact.P.json').read_text())
G = json.loads((ROOT / 'results/arch/hier_contract_1015/hbm_v15.json').read_text())
W, H = G['floorplan']['die_um']
w, h, CH, EDGE = 3 * 302.4 + 2 * 21.6, 2 * 302.4 + 21.6, 21.6, 120.0
cen = lambda b: (b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)
out = {}
for q in ('SW', 'SE', 'NW', 'NE'):
    east, north = q[1] == 'E', q[0] == 'N'
    sm0 = P[f'sm_{q}0']
    x = (W - EDGE - 20.4 - w) if east else EDGE + 20.4
    y = (sm0['y'] + sm0['h'] + CH) if north else (sm0['y'] - CH - h)
    x = round(round(x / 0.216) * 0.216, 3)
    y = round((math.ceil if north else math.floor)(y / 0.27) * 0.27, 3)
    box = (x, y, x + w, y + h)
    conf = []
    for n, b in P.items():
        if isinstance(b, dict) and 'x' in b and b['x'] < box[2] + CH and b['x'] + b['w'] > box[0] - CH and \
                b['y'] < box[3] + CH and b['y'] + b['h'] > box[1] - CH:
            conf.append(n)
    for s in G['slots']:
        o, ol = s.get('origin'), s.get('outline')
        if o and ol and s['name'] != 'die' and o['x'] < box[2] + CH and o['x'] + ol['w'] > box[0] - CH and \
                o['y'] < box[3] + CH and o['y'] + ol['h'] > box[1] - CH:
            conf.append(s['name'])
    hx, hy = x + w / 2, y + h / 2
    ex = W - EDGE / 2 if east else EDGE / 2
    tg = {'G0_vm_pair': [f'vmb_{q}0', f'vmb_{q}1'], 'G1_vm_pair': [f'vmb_{q}2', f'vmb_{q}3'], 'G0_su': [f'su_{q}0'],
          'G1_su': [f'su_{q}1'], 'reducer_qcore': [f'sucore_{q}'], 'vm_hub': [f'vmh_{q}']}
    dist = {}
    for k, names in tg.items():
        cs = [cen(P[n]) for n in names]
        tx, ty = sum(c[0] for c in cs) / len(cs), sum(c[1] for c in cs) / len(cs)
        d = abs(hx - ex) + abs(ty - hy) + abs(tx - ex)
        dist[k] = dict(um=round(d), stages=max(0, math.ceil(d / 500) - 1))
    out[f'su_ovf_{q}'] = dict(origin=dict(x=x, y=y, orient='R0'), outline=dict(w=round(w, 3), h=round(h, 3)),
                              area_mm2=round(w * h / 1e6, 4), conflicts=sorted(set(conf)), route='die-edge column x=%.0f' % ex,
                              to=dist)
p = ROOT / 'results/arch/hbm_die_v15/su_overflow_home_0200/homes.json'
p.write_text(json.dumps(dict(schema='opentallas.hbm_v15.su_overflow_home.v1', status='CANDIDATE (H-SU measures e2e)',
                             homes=out), indent=1) + '\n')
for n, v in out.items():
    print(n, v['origin'], v['outline'], v['area_mm2'], 'conf', v['conflicts'], {k: (d['um'], d['stages']) for k, d in v['to'].items()})
