#!/usr/bin/env python3
"""d4f IDX slots from the plan blocks (d4f_idx_plan.py): idx_s0/s1 hardened scorer clusters (M2-M7, die straps M8,
16 replicated square leaves with regional roots -- H-ELEM assigns closure), idx_sel/link/ctl/q/op tiles; pins FACES_ONLY
(top-down die pin assignment); new slot idx_ctl.     d4f_idx_grant.py GRANTS PLAN_DIR"""
import json, sys
g, pd = sys.argv[1], sys.argv[2]; G = json.load(open(g)); P = json.load(open(pd + '/compact.P.json'))
CELL = dict(idx_s0='ot_hbm_idx_score_static', idx_s1='ot_hbm_idx_score_static', idx_sel='ot_hbm_idx_selector_static',
            idx_link='ot_hbm_idx_topk_link_static', idx_ctl='ot_hbm_idx_ctl_static', idx_q='ot_hbm_idx_query_static', idx_op='ot_hbm_idx_vm_query_static')
S = {s['name']: s for s in G['slots']}
for k, cell in CELL.items():
    b = P[k]; s = S.get(k)
    if s is None:
        s = dict(name=k, parent='die'); G['slots'].append(s)
    clu = k.startswith('idx_s') and k[5:].isdigit()
    s.update(cell=cell, kind='cluster' if clu else 'tile', parent='die', outline=dict(w=b['w'], h=b['h']),
             origin=dict(x=b['x'], y=b['y'], orient='R0'), pins=[], pin_status='FACES_ONLY', plan_block=k, grant='d4f_idx_soft_1017',
             layer_cap='M7' if clu else 'M5', signal_max_layer='M7' if clu else 'M5', pg_layer='M7' if clu else 'M5', strap_layer='M8' if clu else 'M6',
             notes=('IDX scorer: hardened cluster of 16 replicated ~700 um square leaves (4x4, regional roots), view 4.70 mm2 std / 9.45M flops'
                    if clu else 'IDX soft-hierarchy child (contract 50de1fe73)'))
    s.pop('placed_footprint', None)
json.dump(G, open(g, 'w'), indent=1); open(g, 'a').write('\n'); print('idx slots', len(CELL))
