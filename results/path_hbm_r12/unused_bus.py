#!/usr/bin/env python3
"""per-bus breakdown of R10 lane transport 'unused bus bits' (t_banks hub types): width, dir, partner, R10-assigned bits,
core pins allowed on the bus (core_conns) and their widths (pin width = max station bits)."""
import json, sys, collections
W, plan = sys.argv[1:3]
sys.path.insert(0, W + '/tools/die_plan')
import hbm_r10_delta as R10
P = json.load(open(plan + '/die_plan.json'))
ports = {q['id']: q for q in P['ports']}
partner = {}
for ln in P['lanes']:
    a, b = ports[ln['ports'][0]], ports[ln['ports'][-1]]
    for x, y in ((a['src'], b['dst']), (b['dst'], a['src'])):
        partner[(x['part'], x['bus'])] = (y['part'], y['bus'], ln['id'], ln.get('note', ''))
out = {}
for part, tn in (('NW_hub', 'q_hub_nw'), ('NE_hub', 'q_hub_ne')):
    t = P['partition_types'][tn]
    bi = R10.bus_intervals(P, part, t)
    st, rep = R10.resolve_lanes(t, bi, log=lambda *a: None)
    width = {b['name']: (int(b['width']), b['dir'], b['kind']) for b in t['buses']}
    asg = collections.Counter(); pins = collections.defaultdict(dict)
    for s in st:
        r = s.get('r10')
        if not r: continue
        asg[r['bus']] += s['bits']
    for s in t['internal_stations']:
        c = s['conn']
        if not c.startswith('bus:'): continue
        bus = c[4:]
        pn = s['capture'] if str(s['launch']).startswith('face') else s['launch']
        pins[bus][pn] = max(pins[bus].get(pn, 0), s['bits'])
    rows = []
    for bus, (w, d, k) in sorted(width.items()):
        used = min(w, asg.get(bus, 0))
        rows.append(dict(bus=bus, width=w, dir=d, kind=k, assigned=asg.get(bus, 0), unused=w - used,
                         n_pins=len(pins.get(bus, {})), pin_bits=sum(pins.get(bus, {}).values()),
                         partner=partner.get((part, bus))))
    out[tn] = dict(report={k: v for k, v in rep.items()}, buses=rows,
                   unused_total=sum(r['unused'] for r in rows if r['n_pins']),
                   unused_nopin=sum(r['unused'] for r in rows if not r['n_pins']))
json.dump(out, open(sys.argv[3], 'w'), indent=1)
for tn, v in out.items():
    print(tn, 'unused(bus w/ pins)', v['unused_total'], 'unused(bus no pins)', v['unused_nopin'], v['report'])
    for r in sorted(v['buses'], key=lambda r: -r['unused'])[:25]:
        print('  ', r['bus'], r['dir'], r['kind'], 'w', r['width'], 'asg', r['assigned'], 'unused', r['unused'], 'pins', r['n_pins'], r['pin_bits'], r['partner'][:3] if r['partner'] else None)
