#!/usr/bin/env python3
"""d4f COLL hard_v7 parent slots + separate TKM sub-cluster (H-DIE 10-17, COLL helper estimates): coll_<Q> = cluster
1080 x 790 (q2 n1s0: SE/NW/NE) / 1080 x 880 (q3 n2s1: SW), nearest free origin to the v15 home (searched clear of plan
blocks, die-level slots and DIE-CLOCK root keepouts with a 21.6-um halo); tkm_SW = 1740 x 1740 hardened TKM sub-cluster
(32 x ot_hgi_coll_tkm_tile_e86 + 1024x256 buffer) directly N of coll_SW across a 100-um channel (DMA back moved E of coll_SW).  FACES_ONLY until the COLL cluster kits land;
the stale v15 child sub-slots of coll_<Q> are dropped (the kit defines the children).  Patches the plan blocks too.
    d4f_coll_grant.py GRANTS PLAN_DIR"""
import json, sys
g, pd = sys.argv[1], sys.argv[2]
G = json.load(open(g)); P = json.load(open(pd + '/compact.P.json'))
HOME = {'SW': (13765.76, 8874.72, 1080, 880, 'ot_hfd_coll_q3_hard_v5'), 'SE': (13765.76, 12664.72, 1080, 790, 'ot_hfd_coll_q2_hard_v5'),
        'NE': (13765.76, 18713.28, 1080, 790, 'ot_hfd_coll_q2_hard_v5'), 'NW': (14153.872, 22413.28, 1080, 790, 'ot_hfd_coll_q2_hard_v5')}
FACES = dict(E='phy_up, tx_pin_v/flit, rx_pin_v/flit, retry_requested (toward the E column / EP)', N='vm_rq, vm_rr, vm_kq (VM hub)',
             S='ring pr_cw/ccw in/out, rc_v/tag/d, rr_v/tag/d', W='cfg/desc/launch/program status/fault, inj_* (cic), inj_d, del_valid/del_flit/hgi_del_obase')
G['slots'] = [s for s in G['slots'] if not ((s.get('parent') or '').startswith('coll_') and s['name'].startswith('coll_'))]
for s in G['slots']:
    q = s['name'][5:] if s['name'].startswith('coll_') else None
    if q in HOME:
        x, y, w, h, cell = HOME[q]
        s.update(cell=cell, kind='cluster', outline=dict(w=w, h=h), origin=dict(x=x, y=y, orient='R0'), pins=[], pin_status='FACES_ONLY',
                 faces=FACES, grant='d4f_coll_hard_v7_1017', layer_cap='M7', signal_max_layer='M7', pg_layer='M7', strap_layer='M8',
                 notes='COLL hard_v7 parent cluster at d4f params (estimate: sum of child outlines at ~65% fill); kit pending')
        P[f'coll_{q}'] = dict(P[f'coll_{q}'], x=x, y=y, w=w, h=h)
tk = dict(name='tkm_SW', cell='ot_hgi_coll_tkm_m (TP192 tiles ot_hgi_coll_tkm_tile_e86)', kind='cluster', parent='die',
          outline=dict(w=1740.0, h=1740.0), origin=dict(x=14045.76, y=9854.72, orient='R0'), pins=[], pin_status='FACES_ONLY',
          faces=dict(S='del_flit/del_valid in (2,184 b from coll_SW)', W='w_* out (~570 b to coll_SW vmwrite)'),
          grant='d4f_tkm_1017', plan_block='tkm_SW', layer_cap='M7', signal_max_layer='M7', pg_layer='M7', strap_layer='M8',
          notes='separate hardened TKM sub-cluster N of coll_SW (COLL helper recommendation); needs the contract to hoist tkm_m out of hb_coll_SW')
G['slots'] = [s for s in G['slots'] if s['name'] != 'tkm_SW'] + [tk]
P['tkm_SW'] = dict(x=14045.76, y=9854.72, w=1740.0, h=1740.0, orient='R0')
# DMA back SW moves E of coll_SW (31 um channel) so tkm_SW abuts coll_SW's N face across a 100-um channel: the del/w
# buses (~2.9 kb) then cross ONE short channel, no relay stage (H-DIE 10-17)
for s in G['slots']:
    if s['name'] == 'hb_dbk_SW':
        s['origin'] = dict(s['origin'], x=14877.0, y=8877.0); s['home_rule'] = 'd4f: E of coll_SW (tkm_SW takes the N face)'
P['dbk_SW'] = dict(P['dbk_SW'], x=14877.0, y=8877.0)
json.dump(G, open(g, 'w'), indent=1); open(g, 'a').write('\n'); json.dump(P, open(pd + '/compact.P.json', 'w'), indent=1)
print('coll slots + tkm_SW granted')
