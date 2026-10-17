#!/usr/bin/env python3
"""q3h v3 depth: broadcast xs_tap -> farthest tile tap and reduction exit rs -> port, in register stages at hop 373,
vs today's comb (q2o3a0, same rule).  In-cluster terms from cluster_contract.json latency_edges (CB).  Head internal x
read pipeline (DX) is common to both and excluded.  -> q3h_paths.json"""
import json, math, re, collections, os
from pathlib import Path
H = Path(__file__).resolve().parent
HOP = 373.0
a0 = json.load(open(H.parent / 'q2o3a0_sk.json')); I = {i['n']: i for i in a0['insts']}
def bd(a, b):
    return max(0.0, b['x'] - (a['x'] + a['w']), a['x'] - (b['x'] + b['w'])) + max(0.0, b['y'] - (a['y'] + a['h']), a['y'] - (b['y'] + b['h']))
stg = lambda L: max(1, math.ceil(L / HOP))
adj = collections.defaultdict(list)
for b, c, bits, eps in a0['buses']:
    if c in ('head_chain', 'corridor', 'tap') and bits > 1:
        adj[eps[0]].append(eps[1])
dist = {'xs_tap': 0}; q = ['xs_tap']
while q:
    u = q.pop(0)
    for v in adj[u]:
        if v not in dist:
            dist[v] = dist[u] + stg(bd(I[u], I[v])); q.append(v)
bc_today = max(dist[n] for n in I if re.match(r't_\d+_\d+$', n))
red_today = max(stg(bd(I[e[0]], I[e[1]])) for b, c, bits, e in a0['buses'] if b.startswith('bword_'))
TAG = os.environ.get('Q3H_TAG', '')
E = json.load(open(H / f'q3h{TAG}_edges.json')); ed = E['edges']
lat = json.load(open(H / 'cluster_contract.json'))['latency_edges']
near_tap, bco = lat['bc_to_tap']['row3'], lat['bc_to_bco']
age = {h: v['age'] for h, v in E['heads'].items()}
nd = max(e['stages'] for e in ed.values() if e['c'] == 'xslice' and e['src'][1] in ('n_d', 's_d'))   # pads already in head age
bco_e = max(e['stages'] for e in ed.values() if e['c'] == 'xslice' and e['src'][1].startswith('bco'))
far = max(age.values()) + nd + bco + bco_e + near_tap
near = max(age.values()) + nd + near_tap
rs_top = max(e['stages'] for e in ed.values() if e['c'] == 'rsum')
res = dict(variant=E.get('variant'), hop_um=HOP, broadcast=dict(today=bc_today, q3h_die_top_to_head=max(age.values()), q3h_near_band=near, q3h_far_band=far,
                                      delta=far - bc_today, terms=dict(head_age_max=max(age.values()), head_to_bc=nd, bc_to_bco=bco, bco_hop=bco_e, bc_to_tap_row3=near_tap)),
           reduction=dict(today_bword=red_today, q3h_rs_die_top=rs_top, delta_die_top=rs_top - red_today,
                          in_cluster_note=f"CB rs_fabric {lat['rs_fabric']} edges + T_tile + 4 x N_face (bc_to_rs) replaces today's tree_block legs + node"),
           matvec_node_delta_die_top=(far - bc_today) + (rs_top - red_today))
json.dump(res, open(H / f'q3h{TAG}_paths.json', 'w'), indent=1); print(json.dumps(res, indent=1))
