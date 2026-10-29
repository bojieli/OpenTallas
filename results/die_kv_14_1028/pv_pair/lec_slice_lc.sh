#!/bin/bash
# DIE-KV-14b: RTL-vs-RTL equivalence of ot_qwen_tp8_pv_slice_lc_t (G=4) against ot_qwen_tp8_pv_slice_t at the slice
# boundary (copy pins tied to the bits they copy), repo precedent lane8_ltcopy_1025/eq_default.ys (yosys equiv_make /
# equiv_simple -seq 2 / equiv_induct -seq 2 / equiv_status -assert), plus the MUT_LC=1 mutant that must FAIL.
# usage: lec_slice_lc.sh REPO RTL_SUBMODULE_DIR OUTDIR MUT   (run inside openroad/orfs; yosys on PATH)
set -u
R=$1; S=$2; O=$3; M=$4; mkdir -p $O
F="$R/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv $R/rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv $R/rtl/hdc/nearhbm/ot_qwen_tp8_pv_slice_lc_gen.sv $R/results/die_kv_14_1028/pv_pair/lec_wrap.sv $S/ot_qwen_nearhbm_prod.sv $S/ot_hdc_fp32_add_lat.sv $S/ot_hdc_fastfp.sv $S/ot_hdc_fp32_mul_lat.sv $S/ot_hdc_prefix.sv $S/ot_dp_efault.sv $S/ot_sram_1r1w_32x128_m1_bb.v"
cat > $O/eq.ys <<YS
read_verilog -sv -DSYNTHESIS $F
chparam -set MUT_LC $M lec_gate
hierarchy -check -top lec_gold
setattr -mod -unset keep_hierarchy *; proc; flatten; opt_clean; async2sync; opt -fast
rename lec_gold gold
tee -o $O/stat_gold.txt stat
design -stash gold
read_verilog -sv -DSYNTHESIS $F
chparam -set MUT_LC $M lec_gate
hierarchy -check -top lec_gate
setattr -mod -unset keep_hierarchy *; proc; flatten; opt_clean; async2sync; opt -fast
rename lec_gate gate
tee -o $O/stat_gate.txt stat
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 2
equiv_induct -seq 2
tee -o $O/equiv_status.txt equiv_status -assert
YS
yosys -q -l $O/eq.log -s $O/eq.ys > /dev/null 2>&1; rc=$?
echo "MUT_LC=$M yosys rc=$rc"; grep -h "equivalent\|unproven\|Found" $O/equiv_status.txt $O/eq.log 2>/dev/null | tail -4
exit $rc
