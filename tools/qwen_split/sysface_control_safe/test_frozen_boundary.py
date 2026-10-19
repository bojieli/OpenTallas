#!/usr/bin/env python3
"""Real frozen-wrapper negative controls; run in the fleet proof snapshot."""
import json
from pathlib import Path
from check_frozen_boundary import check

b=Path('results/rtl/sysface_physical_proof_1019/frozen_boundary')
w=(b/'ot_pin_regs_wrapper.v').read_text();c=(b/'config.mk').read_text()
o=json.loads(Path('cold/original.json').read_text())
check(w,c,o)
mutants={
 'shortened_reset':(w.replace('rst_n__ot_rl1 <= rst_n__ot_rl0','rst_n__ot_rl1 <= rst_n'),c),
 'wrong_input_D':(w.replace('prog_rx_v__ot_q <= prog_rx_v;','prog_rx_v__ot_q <= rst_n;'),c),
 'wrong_output_D':(w.replace('cfg_tx_we__ot_q <= cfg_tx_we__ot_pr;','cfg_tx_we__ot_q <= rst_n;'),c),
 'wrong_clock':(w.replace('always @(posedge ck)','always @(posedge rst_n)',1),c),
 'missing_reset_landing':(w,c.replace('export OT_RST_LAND = 1','export OT_RST_LAND = 0')),
}
for name,(mw,mc) in mutants.items():
 assert mw!=w or mc!=c
 try:check(mw,mc,o)
 except AssertionError:print('EXPECTED_REFUSAL',name)
 else:raise AssertionError('escaped frozen-boundary mutant '+name)
print('FROZEN_BOUNDARY_GUARDS_PASS mutants5')
