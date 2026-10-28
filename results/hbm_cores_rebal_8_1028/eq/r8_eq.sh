#!/usr/bin/env bash
# REBAL-8 (b): WCOPY=0 (default) pinned bank == origin/main pinned bank (yosys equiv_make/equiv_induct, SRAM blackbox)
set -euo pipefail
W=$1; O=$2; mkdir -p $O/gold
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
S=rtl/hbm_accel/generic/adapters/static_su/data_store
for f in ot_hbm_su_static_pinned_bank.sv ot_hbm_su_static_data_store.sv ot_hbm_su_static_bank6_clock_physical.sv; do
  git -C $W show origin/main:$S/$f > $O/gold/$f; done
BB=$W/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v
for top in ot_hbm_su_static_bank6_clock_physical ot_hbm_su_static_pinned_bank; do
$Y -q -l $O/eq_$top.log -p "
read_verilog -sv -lib $BB
read_verilog -sv $O/gold/ot_hbm_su_static_pinned_bank.sv $O/gold/ot_hbm_su_static_data_store.sv $O/gold/ot_hbm_su_static_bank6_clock_physical.sv
hierarchy -top $top; proc; flatten; opt_clean; rename $top gold; design -stash gold
read_verilog -sv -lib $BB
read_verilog -sv $W/$S/ot_hbm_su_static_pinned_bank.sv $W/$S/ot_hbm_su_static_data_store.sv $W/$S/ot_hbm_su_static_bank6_clock_physical.sv
hierarchy -top $top; proc; flatten; opt_clean; rename $top gate; design -stash gate
design -copy-from gold -as gold gold; design -copy-from gate -as gate gate
equiv_make gold gate eq; hierarchy -top eq; async2sync; equiv_simple -seq 2; equiv_induct -seq 2; equiv_status -assert"
echo "$top: $(grep -E 'Found .* equiv|proven|unproven' $O/eq_$top.log | tail -2 | tr '\n' ' ')"
done
