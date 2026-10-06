#!/bin/bash
# CLAUDE HBM-ABSTRACTS (hub): connectivity proof of a quarter envelope: (1) Verilator lint of the wrapper with the REAL
# lane RTL; (2) one-seed simulation with the lane sim stub against the generator's reference (exit 1 on mismatch);
# (3) negative control (lane 1's first per-lane bit off by one) must FAIL.   bench.sh <quarter> <outdir>  (run in src)
set -u; q=$1; O=$2; m=hfd_$q; mkdir -p $O
python3 tools/hbm_die_views.py ports --master $m --out $O/ports > /dev/null
python3 tools/hbm_hub_quarter_gen.py --quarter $q --ports $O/ports/$m/ports.json --out $O/gen > $O/plan.log
cmp $O/gen/$m.sv physical/hbm_accel_die_views/$q/rtl/$m.sv && echo "committed RTL reproduced" > $O/repro.txt
if [ $q = hc ]; then LS="rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv"
else LS="rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41/ot_hdc_fsqrt_c12.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv"; fi
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-PINCONNECTEMPTY -Wno-VARHIDDEN -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-SYNCASYNCNET -Wno-UNOPTFLAT -Wno-CASEINCOMPLETE -Wno-BLKSEQ -Wno-MULTIDRIVEN --top-module $m $O/gen/$m.sv $LS > $O/lint.log 2>&1; echo "lint_rc=$?" > $O/result.txt
grep -c "%Warning-\(UNDRIVEN\|PINMISSING\|IMPLICIT\)" $O/lint.log >> $O/result.txt
cd $O/gen
iverilog -g2012 -o sim tb_$m.sv $m.sv *_simstub.sv && vvp -n sim > pos.log; echo "pos_rc=$?" >> ../result.txt; grep OT_RESULT pos.log >> ../result.txt
iverilog -g2012 -o simn tb_$m.sv ${m}_neg.sv *_simstub.sv && vvp -n simn > neg.log; echo "neg_rc=$?" >> ../result.txt; grep OT_RESULT neg.log >> ../result.txt
cat ../result.txt
