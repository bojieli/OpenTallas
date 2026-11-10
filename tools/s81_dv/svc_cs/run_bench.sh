#!/bin/bash
# run_bench.sh REPO OUTDIR BOX [MUTANT_SED [MUT_FILE]]: Verilator lock-step bench of an S81 svc census-safe box copy.
# --x-initial unique + random register init; seeds 1..NSEED.  MUTANT_SED: a sed expression applied to MUT_FILE
# (default the box's _cs file, a copy in OUTDIR) -- a mutant must FAIL.
set -u
R=$1; O=$2; BOX=$3; MS=${4:-}; NSEED=${NSEED:-3}
H=$R/rtl/hdc; S=$R/rtl/dsrom_sys/s81_svc; SM=$R/rtl/dsrom_sys/s81_dv/su_sm; T=$R/tools/s81_dv/svc_cs
LIB="$R/rtl/proto/ot_fp32_add_rne_pipe.sv $H/ot_hdc_sfu.sv $H/ot_hdc_delay.sv $H/ot_hdc_fpu.sv $H/ot_hdc_fp32_mul_pipe.sv
 $H/ot_hdc_fastfp_lat_f12.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fp32_f12.sv $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv
 $H/ot_hdc_fp32_mul_lat.sv $H/v41/ot_hdc_fsqrt.sv $H/v41x/ot_hdc_v41x_sfu.sv $H/v41x/ot_dsrom_su_softmax_add.sv
 $H/v41x/ot_dsrom_su_softmax_m9.sv $H/v41x/ot_dsrom_su_softmax_f12r.sv $H/v41x/ot_dsrom_su_softmax_add6.sv
 $H/v41x/ot_dsrom_su_fdiv_f12.sv $H/v41x/ot_dsrom_su_add6.sv $H/ot_hdc_cg.sv"
CSLIB="$S/ot_s81_svc_fp32_f12_cs.sv $S/ot_s81_svc_exp_cs.sv $S/ot_s81_svc_fdiv_f12_cs.sv"
case $BOX in
 sml) TOP=tb_sml_fold2_cs; F="$SM/ot_s81_su_sml_fold2.sv"; CS=$S/ot_s81_su_sml_fold2_cs.sv ;;
 smd) TOP=tb_smd_fold2_cs; F="$SM/ot_s81_su_smd_fold2.sv"; CS=$S/ot_s81_su_smd_fold2_cs.sv ;;
 smc) TOP=tb_smc_cs; F="$R/rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv"; CS=$S/ot_s81_su_smc_cs.sv ;;
 smr) TOP=tb_smr_cs; F="$R/rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv"; CS=$S/ot_s81_su_smr_cs.sv ;;
 *) echo "unknown box $BOX"; exit 2 ;;
esac
rm -rf $O; mkdir -p $O
MF=${5:-$CS}
for f in $CS $CSLIB; do cp $f $O/; done
if [ -n "$MS" ]; then sed -i "$MS" $O/$(basename $MF); cmp -s $MF $O/$(basename $MF) && { echo "MUTANT NOT APPLIED"; exit 3; }; fi
CSF=""; for f in $CS $CSLIB; do CSF="$CSF $O/$(basename $f)"; done
verilator --binary -j 8 --x-initial unique --x-assign unique -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
  -DSYNTHESIS --top-module $TOP -Mdir $O/obj $LIB $F $CSF $T/tb_${BOX}_cs.sv > $O/build.log 2>&1 || { echo "BUILD FAIL"; tail -20 $O/build.log; exit 4; }
rc=0
for s in $(seq 1 $NSEED); do
  $O/obj/V$TOP +verilator+seed+$s +verilator+rand+reset+2 +seed=$s > $O/run_$s.log 2>&1 || true
  l=$(grep -E "PASS|FAIL" $O/run_$s.log | tail -1); echo "$BOX seed$s: ${l:-NO RESULT $(tail -2 $O/run_$s.log)}"
  echo "$l" | grep -q PASS || rc=1
done
exit $rc
