#!/bin/bash
# HBM-CORES-B 11-12: RDREG 0 (this branch) == origin/main ot_hbm_sm_pv_merge, PUBLISH 1 and 0, yosys equiv
# (real behavioural 64x512 stack + real fp32 adders on both sides; no equiv_struct). Run from the repo root.
set -u
O=${O:-/tmp/pvm_eq0_$$}; mkdir -p $O
git show origin/main:rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv > $O/gold.sv
C="rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
for P in 1 0; do
cat > $O/eq_p$P.ys <<EOY
read_verilog -sv -DSYNTHESIS -DOT_FP_DATA_NORST $C $O/gold.sv
chparam -set PUBLISH $P ot_hbm_sm_pv_merge
hierarchy -top ot_hbm_sm_pv_merge
proc; flatten; opt_clean; memory -nomap; memory_map; opt -purge; async2sync
rename ot_hbm_sm_pv_merge gold
design -stash gold
read_verilog -sv -DSYNTHESIS -DOT_FP_DATA_NORST $C rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv
chparam -set PUBLISH $P ot_hbm_sm_pv_merge
hierarchy -top ot_hbm_sm_pv_merge
proc; flatten; opt_clean; memory -nomap; memory_map; opt -purge; async2sync
rename ot_hbm_sm_pv_merge gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status
equiv_status -assert
EOY
yosys -q -l $O/eq_p$P.log -s $O/eq_p$P.ys; echo "PUBLISH=$P rc=$?"
done
