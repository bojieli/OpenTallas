#!/usr/bin/env python3
"""TOK-S81-GAPS/G8R (10-18): bind_table_p4m.json = bind_table_p4l3.json with the land plan of the equal-N plan p4m.

p4m/plan.json = p4l/plan.json + equal station count per multi-lane bundle (tools/s81_dv/dv_plan_eqn.py: hf_7N l0 and
the 24 x_frame bundles, 73 half-cycle stations at the midpoint of each padded lane's longest straight piece).
landing/p4m = dv_land_pilot.py agebundle of landing/p4m_in (p4l2 land plan with the padded lanes' stages, s1 estimated).
Frame lk straps: dv_bind derives them from this land plan (K = max lane K of the frame bundle, G8R2); with equal N every
lane lands at one age and the derived values equal the table's static strap_values (bind_case frame_lk.differs_from_table
empty).  dv_plan_eqn.py inserts the padding station at the arc-length midpoint of the lane's longest wire interval
(Codex G8R recovery 10-18: stations may straddle a wire turn).
"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
B = ROOT / 'results/arch/s81_dv_1016/bind'
T = json.load(open(B / 'bind_table_p4l3.json'))
T['land_plan'] = 'results/arch/s81_dv_1016/landing/p4m/land_plan.json'
T['note'] += ('; TOK-S81-GAPS/G8R 10-18/19: plan p4m (equal N per bundle, dv_plan_eqn.py) + land plan p4m; frame x lanes get '
              'the G1 hop-0 ICG (dv_bind frame_hop0_gates) (bind/mk_table_p4m.py)')
(B / 'bind_table_p4m.json').write_text(json.dumps(T, indent=1) + '\n')
print('bind_table_p4m.json written')
