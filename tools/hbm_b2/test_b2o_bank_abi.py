#!/usr/bin/env python3
"""Tests for b2o_bank_abi.py on a synthetic hub: roles, calendars, owner order, tied dq, miswired calendar refused."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2o_bank_abi as A  # noqa: E402


def bank(name, cal, k, dq):
    lo, hi = 3 * k, 3 * k + 2
    return f"""    hfd_vms_bank_native_q0_faces {name} (
        .dq({dq}),
        .rq0(w_u_fvp_Q{k}_rq0[16:0]),
        .rslot(w_{cal}_rslot[{hi}:{lo}]),
        .wslot(w_{cal}_wslot[{hi}:{lo}]),
        .wq1(w_u_smw_Q_q0_wq_t0[280:0])
    );
"""


def src(cal_s='u_calendar_Q_q0'):
    banks = ''.join(bank(f'u_u_vmb_Q{k}', 'u_calendar_Q_q1', k, 'w_u_vmdel_Q0_dq[280:0]') +
                    bank(f'u_u_vmb_Q{k}_mu1', cal_s, k, "{281{1'b0}}") for k in range(2))
    return ("module ot_vms_bank_q0_faces_core(); ot_vms_bank_q0_faces_body #(.RG(5),.WG(2),.EG_WIDE(1)) bank(); endmodule\n"
            f"module hbm_arch_q_hub__q_hub_x (input clk);\n{banks}endmodule\n")


r = A.build(src())
h = r['hubs']['hbm_arch_q_hub__q_hub_x']
assert r['calendar_roles']['hbm_arch_q_hub__q_hub_x'] == {'N': 'u_calendar_Q_q1', 'S': 'u_calendar_Q_q0'}
s1 = [x for x in h if x['role'] == 'S' and x['k'] == 1][0]
assert s1['slot_lsb'] == 3 and s1['write'][6]['leaf'] == 'tied0' and s1['read'][0]['leaf'] == 'u_fvp_Q1', s1
assert r['body']['dq_owner'] == 6
try:
    A.build(src('u_calendar_Q_q1').replace('u_u_vmb_Q1_mu1', 'u_u_vmb_Q1_mu1').replace('rslot[5:3]),\n        .wslot(w_u_calendar_Q_q1_wslot[5:3]),\n        .wq1', 'rslot[2:0]),\n        .wslot(w_u_calendar_Q_q1_wslot[2:0]),\n        .wq1'))
    raise SystemExit('miswired calendar accepted')
except ValueError:
    pass
print('PASS 4 checks')
