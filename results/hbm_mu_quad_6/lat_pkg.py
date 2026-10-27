#!/usr/bin/env python3
"""HBM-MU-QUAD-3 latency package (reused by HBM-MU-QUAD-6): per-lane die cycles (latency.lanes) and per-connection station cycles (internal
stations + ft-slot stations, register count = cycles) of PLAN vs BASE, for TOK-HBM.  Usage: lat_pkg.py BASE PLAN OUT"""
import json, sys, hashlib, collections
def load(d):
    s = open(d + '/die_plan.json').read(); P = json.loads(s)
    st = collections.defaultdict(int)
    for tn, t in P['partition_types'].items():
        for s_ in t.get('internal_stations', []):
            k = (tn, 'int', str(s_.get('conn')))
            st[k] = max(st[k], len(s_.get('regs_um', [])))
        for f in t.get('ft_slots', []):
            k = (tn, 'ft', str(f.get('lane') or f.get('name')))
            st[k] = max(st[k], len(f.get('regs_um', [])))
    return P, st, hashlib.sha256(s.encode()).hexdigest()
B, sb, hb = load(sys.argv[1]); P, sp, hp = load(sys.argv[2])
lb, lp = B['latency']['lanes'], P['latency']['lanes']
lanes = {k: dict(base=lb.get(k, {}).get('cycles'), plan=v['cycles']) for k, v in lp.items()}
ch = {k: v for k, v in lanes.items() if v['base'] != v['plan']}
stc = [dict(type=k[0], kind=k[1], conn=k[2], base=sb.get(k), plan=v) for k, v in sorted(sp.items()) if sb.get(k) != v]
out = dict(schema='opentallas.hbm.lat_package.v1', lane="HBM-MU-QUAD-6", base_sha256=hb, plan_sha256=hp,
           note='cycles = registered stations (static schedule); per-conn value = max over bits; UNCHECKED until TOK-HBM reprices',
           lanes=lanes, lanes_changed=ch, stations_changed=stc,
           summary=dict(lanes=len(lanes), lanes_changed=len(ch), stations_changed=len(stc),
                        station_cycles_added=sum((x['plan'] or 0) - (x['base'] or 0) for x in stc)))
json.dump(out, open(sys.argv[3], 'w'), indent=1)
print(json.dumps(out['summary']), json.dumps(ch))
