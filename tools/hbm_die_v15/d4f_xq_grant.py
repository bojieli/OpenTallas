#!/usr/bin/env python3
"""d4f r4 XQL pair-store slots (one per contract instance, named as the instance so the die generator homes it exactly)
from the d4f_xq_plan.py plan blocks.  eg = H-SM pegress x6 (369.36 sq, faces N xw / W bq_d / S rwq / E ctl, 5 regional
clock entries; native pending); bd = cl2_bdring; bfq<g> = cl2_bfqg (native PASS, 20 clock ports).   d4f_xq_grant.py GRANTS PLAN_DIR"""
import json, re, sys
g, pd = sys.argv[1], sys.argv[2]; G = json.load(open(g)); P = json.load(open(pd + '/compact.P.json'))
CELL = dict(eg='ot_hgi_sm_xload_xq_pegress', bd='ot_hgi_sm_xload_cl2_bdring', bfq='ot_hgi_sm_xload_cl2_bfqg')
G['slots'] = [s for s in G['slots'] if not s['name'].startswith('xq_')]
n = 0
for k, b in P.items():
    m = re.fullmatch(r'xq_(SW|NW)_p(\d)_(eg|bd|bfq)(\d?)', k)
    if not m:
        continue
    kind = m.group(3)
    s = dict(name=k, cell=CELL[kind], kind='tile', parent='die', outline=dict(w=b['w'], h=b['h']), origin=dict(x=b['x'], y=b['y'], orient=b['orient']),
             plan_block=k, grant='d4f_xq_pairgap_1017', layer_cap='M5', signal_max_layer='M5', pg_layer='M5', strap_layer='M6',
             pins=[], pin_status='FACES_ONLY' if kind == 'eg' else 'MACRO_LEF_PINS',
             faces=dict(N='xw 2,063 + status (to the SM 2p/2p+1 xw windows)', W='bq_d 2,048 from bd', S='rwq 1,024 from the bfq stack', E='43 ctl') if kind == 'eg' else None,
             notes=f'XQL pair store {m.group(1)} p{m.group(2)} in the SM pair gap (d4f r4)')
    G['slots'].append(s); n += 1
json.dump(G, open(g, 'w'), indent=1); open(g, 'a').write('\n'); print('xq slots', n)
