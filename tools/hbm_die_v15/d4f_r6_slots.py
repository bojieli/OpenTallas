#!/usr/bin/env python3
"""d4f r6 structural slot moves (H-DIE-R6 2026-10-17, coordinator run3 over-reach review):
  wbk_SW / wbk_NW : the K write port (ot_hbm_svc_wb_kport) feeds 8 DISTINCT 1,148-b buses to vmks_<Q>0..7 in the PC band
                    and takes 2,312 b from hb_dbk_<Q>.  Beside the DMA back (r5/20d48a725) the 9,184 b ran 9-15 mm
                    (123 kbit-mm per quarter).  r6: own slot at the E end of the PC band (right of pc_<Q>7, clear of the
                    PHY and the SM column ends), so only the 2,312-b dbk feed crosses the die (~67 kbit-mm per quarter).
  hb_argmax       : 107 um sq argmax (ot_hbm_argmax_static_sw_vm) fitted no IDX block (OWNER-BLOCK MISFIT); own slot E of
                    idx_op in the idx_ctl/q/op row (its 2,056 + 136 b peer is hb_idx__ctl).
The slot named after the instance is the instance's home (die_case_v16 eslot) when the contract gives no slot; wbk/sfup
contract slots are retargeted by H-NETLIST slots_r6_d4f (2a2ccaa4e) or die_case_v16 --slot-map.
    d4f_r6_slots.py GRANTS PLAN_DIR"""
import json, sys
g, pd = sys.argv[1], sys.argv[2]
G = json.load(open(g)); P = json.load(open(pd + '/compact.P.json'))
S = {s['name']: s for s in G['slots']}
pc7s, pc7n = P['pc_SW7'], P['pc_NW7']
x0 = round(pc7s['x'] + pc7s['w'] + 108.0, 3)                       # 108 um channel E of pc_<Q>7
moves = {'wbk_SW': (x0, round(pc7s['y'] + 21.6, 3), 'R0'),
         'wbk_NW': (x0, round(pc7n['y'] + pc7n['h'] - 21.6 - S['wbk_NW']['outline']['h'], 3), 'MX')}
for n, (x, y, o) in moves.items():
    s = S[n]; s['origin'] = dict(x=x, y=y, orient=o)
    s['r6'] = 'PC band E end, beside its 8 vmks consumers (H-DIE-R6 coordinator item 7)'
idx_op = P['idx_op']
if 'hb_argmax' not in S:
    G['slots'].append(dict(name='hb_argmax', cell='ot_hbm_argmax_static_sw_vm', kind='tile', parent='die',
                           outline=dict(w=118.8, h=118.8),
                           origin=dict(x=round(idx_op['x'] + idx_op['w'] + 43.2, 3), y=idx_op['y'], orient='R0'),
                           pins=[], pin_status='FACES_ONLY', grant='d4f_r6_slot_1017',
                           notes='own slot E of idx_op (peer hb_idx__ctl 2,192 b); was OWNER-BLOCK MISFIT in run3'))
json.dump(G, open(g, 'w'), indent=1); open(g, 'a').write('\n')
print(json.dumps({n: S[n]['origin'] for n in moves} | {'hb_argmax': next(s for s in G['slots'] if s['name'] == 'hb_argmax')['origin']}))
