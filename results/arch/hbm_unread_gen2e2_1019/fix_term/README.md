# F-T: terminal_chain_control (116 bits) -- real fix

hcb_<q>7 (CPI1/CPO1) is the LAST bank of each HC quarter ring chain: sum_out/f_out go to bank 0's chain-exit relay, the
forward descriptor o_v/o_ss/o_nv/o_wa/o_xa (29 b) has no consumer. New master `ot_hbm_hc_bankq_term_static`
(rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_bankq_term_static.sv; die copy scoped_d4g/hcbt.sv, l14 identifier-only
namespace) has no forward ports and no o_* CPO face registers; everything else is cycle-exact.
Layer `l20t_hc_bankq_term.py` (fail-closed: removed port with a sink, non-CPI1/CPO1 bank, retained outputs differ).
Bind: unread 70,320 -> 70,204, structural 0, functional PASS 1284. Bench PASS / mutant TMUT=3 FAIL (logs here).

SAFE-DESIGN checklist: 1 pins PASS (all retained outputs are flops, inputs land in CPI flops) - 2 reach PASS (port subset,
same slot) - 3 fanout PASS - 4 depth PASS (no logic added) - 5 storage PASS - 6 floorplan PASS (29 fewer face pins) -
7 clock PASS (single clk) - 8 schedule PASS (no cycle changed on retained outputs). Source-only: synth in next GEN.
