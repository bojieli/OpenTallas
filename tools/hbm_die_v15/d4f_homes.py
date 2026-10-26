#!/usr/bin/env python3
"""d4f explicit homes for the translated (non-plan) slots: E-column hub items and the 9th service bands.  d4f_homes.py PLAN_DIR"""
import json, sys
N = sys.argv[1]; P = json.load(open(N + '/compact.P.json')); W, H = json.load(open(N + '/compact.metrics.json'))['die_um']
c0 = P['hc_eng']['x']; eN = min(P[k]['y'] for k in P if k.startswith('ep_N')); eS = min(P[k]['y'] for k in P if k.startswith('ep_S'))
h = {'host_N': dict(x=c0, y=round(H - 20 - 1652.424, 3), orient='MX', rule='d4f: N die edge in the E column (UCIe shoreline)'),
     'host_cp': dict(x=round(c0 + 360, 3), y=round(H - 20 - 432, 3), orient='R0', rule='d4f: beside host_N at the N edge'),
     'hb_ckgen': dict(x=c0, y=round(eN + 515.2 + 100, 3), orient='R0', rule='d4f: E column centre above the ep_N row'),
     'vm_status4': dict(x=c0, y=eS, orient='R0', rule='d4f: E column beside the hubs, below hc_eng'),
     'hc_eng_tgt': dict(x=c0, y=eN, orient='R0', rule='d4f: programme collar on hc_eng N face'),
     'hc_tbl_tgt': dict(x=round(c0 + 186, 3), y=eN, orient='R0', rule='d4f: programme collar on hc_eng N face'),
     'svc_SW_s8': dict(x=round(P['pc_SW0']['x'] - 100 - 1036.8, 3), y=P['pc_SW0']['y'], orient='R0', rule='d4f: 9th service band west of pc_SW0'),
     'svc_NW_s8': dict(x=round(P['pc_NW0']['x'] - 100 - 1036.8, 3), y=round(P['pc_NW0']['y'] + P['pc_NW0']['h'] - 399.6, 3), orient='MX', rule='d4f: 9th service band west of pc_NW0')}
print(json.dumps(h, indent=1))
