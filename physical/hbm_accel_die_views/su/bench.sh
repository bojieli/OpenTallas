#!/bin/bash
# CLAUDE HBM-ABSTRACTS (hub): connectivity proof of a quarter envelope: (1) Verilator lint of the wrapper with the REAL
# lane RTL; (2) one-seed simulation with the lane sim stub against the generator's reference (exit 1 on mismatch);
# (3) negative control (lane 1's first per-lane bit off by one) must FAIL.   bench.sh <quarter> <outdir>  (run in src)
set -u; q=$1; O=$2; m=hfd_$q; [ $q = hcp ] && m=hfd_hc; mkdir -p $O   # hcp: safe-hbm S-C1 HC quarter (pin-registered lane)
python3 tools/hbm_die_views.py ${VARIANT:+--variant $VARIANT} ports --master $m --out $O/ports > /dev/null
python3 tools/hbm_hub_quarter_gen.py --quarter $q --ports $O/ports/$m/ports.json --out $O/gen ${TWO_SIDED:+--two-sided} > $O/plan.log
cmp $O/gen/$m.sv physical/hbm_accel_die_views/$q/rtl/$m.sv && echo "committed RTL reproduced" > $O/repro.txt
if [ $q = hcp ]; then LS="rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv"
elif [ $q = hc ]; then LS="rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv"
else LS="rtl/hdc/v41x/phys/ot_hdc_v41x_su_c12_phys.sv rtl/hdc/v41x/ot_hdc_v41x_vec_lane_c12.sv rtl/hdc/v41x/ot_hdc_v41x_sfu_c12.sv rtl/hdc/v41x/ot_hdc_v41x_vec_side_c12.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41/ot_hdc_fsqrt_c12.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv"; fi
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-PINCONNECTEMPTY -Wno-VARHIDDEN -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC -Wno-SYNCASYNCNET -Wno-UNOPTFLAT -Wno-CASEINCOMPLETE -Wno-BLKSEQ -Wno-MULTIDRIVEN --top-module $m $O/gen/$m.sv $LS > $O/lint.log 2>&1; echo "lint_rc=$?" > $O/result.txt
grep -c "%Warning-\(UNDRIVEN\|PINMISSING\|IMPLICIT\)" $O/lint.log >> $O/result.txt
cd $O/gen
iverilog -g2012 -o sim tb_$m.sv $m.sv *_simstub.sv && vvp -n sim > pos.log; echo "pos_rc=$?" >> ../result.txt; grep OT_RESULT pos.log >> ../result.txt
# su inject-ownership gate (tb_out_q<qid>.mem): every quarter id must match its own reference, and the no-gate mutant
# (every quarter drives t_coll) must FAIL
if [ -f tb_out_q1.mem ]; then
  for qd in 1 2 3; do iverilog -g2012 -Ptb.QID=$qd -o sim$qd tb_$m.sv $m.sv *_simstub.sv && vvp -n sim$qd > pos$qd.log; echo "pos_rc=$?" | sed 's/pos_rc=0$/pos_rc=0/;s/pos_rc=[1-9].*/pos_rc_FAIL q'$qd'/' >> ../result.txt; grep OT_RESULT pos$qd.log >> ../result.txt; done
  iverilog -g2012 -Ptb.QID=1 -DOT_HFD_SU_MUT_NOGATE -o simg tb_$m.sv $m.sv *_simstub.sv && vvp -n simg > gmut.log; echo "gate_mut_rc=$?" >> ../result.txt; grep OT_RESULT gmut.log | sed 's/^OT_RESULT/GATE_MUT/' >> ../result.txt
fi
iverilog -g2012 -o simn tb_$m.sv ${m}_neg.sv *_simstub.sv && vvp -n simn > neg.log; echo "neg_rc=$?" >> ../result.txt; grep OT_RESULT neg.log >> ../result.txt
cat ../result.txt
