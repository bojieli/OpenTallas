#!/bin/bash
# HBM-CORES-KITS-26: per-quarter reset copies vs the master before the change (old_sel.sv = git show ea152b24736:rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv with both modules renamed _old).
# NMUT=0 must print TB_SEL_RSTQ PASS; NMUT=4 (quarter 3 releases one edge early) must FAIL.
R=rtl/hbm_accel/index; M=physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
git show ea152b24736:$R/ot_hbm_idx_selector_static_sel.sv | sed -e "s/\bot_hbm_idx_selector_static_sel_core\b/ot_hbm_idx_selector_static_sel_core_old/g; s/^module ot_hbm_idx_selector_static_sel #/module ot_hbm_idx_selector_static_sel_old #/" > /tmp/old_sel.sv
for m in 0 4; do iverilog -g2012 -s tb_sel_rstq -Ptb_sel_rstq.NMUT=$m -Ptb_sel_rstq.NCYC=6000 -Ptb_sel_rstq.NRST=4 -o /tmp/s$m.vvp $R/ot_hbm_idx_selector_static_sel.sv /tmp/old_sel.sv $R/ot_hbm_idx_selector_compact.sv $R/ot_hbm_idx_compact_tree.sv $M results/hbm_selector_1030_rstq/tb_sel_rstq.sv && vvp /tmp/s$m.vvp | tail -n 3; done
