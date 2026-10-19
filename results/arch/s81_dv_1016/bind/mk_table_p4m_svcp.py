#!/usr/bin/env python3
"""TW3-S81/LAYERS/SVCP4M (10-19): bind_table_p4m_svcp.json = bind_table_p4l3.json (incl. the TOK-S81-GAPS/SVCP svc_rs
'unlinked_out_bits' spare-output rules) with the land plan of the equal-N plan p4m -- i.e. bind_table_p4m.json + the
SVCP spare-output rules.  Used with plan p4m_svcp/plan.json (= p4m + the abutted P-path lane pr_09_07, 514 b, 110 um,
rsv_09 ro W -> rsv_07 ri E; dv_plan_eqn.py on the SVCP p4l plan; no station / landing: the lane is abutted).
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
B = ROOT / 'results/arch/s81_dv_1016/bind'
T = json.load(open(B / 'bind_table_p4l3.json'))
T['land_plan'] = 'results/arch/s81_dv_1016/landing/p4m/land_plan.json'
T['note'] += ('; TOK-S81-GAPS/G8R 10-18/19: plan p4m (equal N per bundle, dv_plan_eqn.py) + land plan p4m; frame x lanes get '
              'the G1 hop-0 ICG (dv_bind frame_hop0_gates) (bind/mk_table_p4m.py)'
              '; TW3-S81/LAYERS/SVCP4M 10-19: + SVCP svc_rs unlinked_out_bits spare-output rules for plan p4m_svcp '
              '(p4m + pr_09_07) (bind/mk_table_p4m_svcp.py)')
(B / 'bind_table_p4m_svcp.json').write_text(json.dumps(T, indent=1) + '\n')
print('bind_table_p4m_svcp.json written')
