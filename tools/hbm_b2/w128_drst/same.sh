#!/bin/bash
# are plain/feed/term pair masters the same circuit? (leaves + SRAMs black boxes)
cd "$(dirname "$0")"; Y=$HOME/.local/opentallas-tools/bin/yosys; mkdir -p same
for v in feed term; do
cat > same/$v.ys <<YS
read_verilog -lib src/ot_sram_1r1w_1024x256_m2_r2c2_bb.v src/ot_sram_1r1w_128x256_m1_r2c2_bb.v
read_verilog -sv -lib -DSYNTHESIS src/ot_hdc_v41x_hcp.sv
read_verilog -sv plain/pair_compact/ot_hbm_hc_bank128_pair_core.sv
rename ot_hbm_hc_bank128_pair_core gold
read_verilog -sv $v/pair_compact/ot_hbm_hc_bank128_pair_core.sv
rename ot_hbm_hc_bank128_pair_core gate
proc; opt_clean
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 2
equiv_induct
equiv_status -assert
YS
$Y -ql same/$v.log -s same/$v.ys; echo "plain==$v rc=$?"; grep -E "Found .* \\\$equiv|unproven" same/$v.log | tail -2
done
