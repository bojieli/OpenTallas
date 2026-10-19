#!/usr/bin/env python3
"""H-D4G 10-17: view binding table of a d4g GEN (v16_views.py plan) -- every closed routed view that still applies
(port signature equal to the d4g contract) is BOUND; the units the RTL lanes HBM-B-RTL1..3 change are marked OPEN
BINDINGS (bound as their d4f RTL / view in this diagnostic, rebind when the lane lands).
    d4g_bindings.py --views VPLAN/views.json --grants results/arch/hbm_die_d4g/grants_d4g.json --out OUT.json
"""
import argparse, collections, json, re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--views', required=True); ap.add_argument('--grants', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    V = json.load(open(a.views)); G = json.load(open(a.grants))
    opens = G['d4g']['open_bindings']
    rows, cnt = [], collections.Counter()
    for c, v in sorted(V.items()):
        insts = v['instances']
        units = sorted({o['unit'] for o in opens for n in insts if re.match(o['regex'], n)})
        lanes = sorted({o['lane'] for o in opens if o['unit'] in units})
        st = ('OPEN_' if units else '') + ('BOUND_ROUTED' if v['kind'] != 'SYNTH' else 'SYNTH')
        cnt[st] += 1
        rows.append(dict(cell=c, master=v['master'], instances=len(insts), kind=v['kind'], view=v.get('view_dir'),
                         status=st, open_units=units, rtl_lanes=lanes))
    out = dict(schema='opentallas.hbm.d4g.bindings.v1', views=a.views, summary=dict(cnt), cells=rows,
               rule='BOUND_ROUTED = closed routed view on main whose pins equal the d4g contract ports (v16_views ROUTED_UNBOUND: '
                    'lineage/native qualification is the binding owner\'s); SYNTH = no applicable routed view, mapped-netlist ETM; '
                    'OPEN_* = unit the RTL lanes change (VM, SU, HC, IDX, COLL, host): diagnostic binding until the lane lands')
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps(out['summary']))


if __name__ == '__main__':
    main()
