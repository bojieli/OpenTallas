#!/bin/bash
# hbm-forks 2026-10-09: exact benches of the HGI-1 forks.   run_bench.sh <bench> <out dir>   (from the source root)
#   env MUT=<define> builds the named negative mutant (+define+<MUT>); the bench must then print FAIL.
# Prints the bench's PASS/FAIL summary line; exit 0 iff PASS.
set -u
B=$1; O=$2; mkdir -p $O; G=rtl/hbm_accel/generic
D=""; [ -n "${MUT:-}" ] && D="-D$MUT"
case $B in
  cmdproc)
    S="$G/ot_hgi_cfg.sv $G/ot_hgi_cmdproc_core.sv $G/ot_hgi_cmdproc_core_m.sv $G/ot_hgi_cmdproc.sv
       physical/hbm_accel_die_views/cmdproc/rtl/ot_hfd_cmdproc20_m.sv physical/asap7_memory_macros_v2/ot_sram_2rw_512x64_m4_r2c2/ot_sram_2rw_512x64_m4_r2c2.v
       $G/tb/tb_hgi_cmdproc.sv"; TOP=tb_hgi_cmdproc; TAG=HGI_CMDPROC; RUNDIR=$G/tb;;
  argmax|argmax_f1)
    AM=physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv
    if [ "${MUT:-}" = MUT_TIE ]; then     # mutant: the tree's tie-break keeps the HIGHER index
      sed 's/ti\[lv\]\[2\*e\] < ti\[lv\]\[2\*e+1\]/ti[lv][2*e] > ti[lv][2*e+1]/' $AM > $O/argmax_mut.sv
      cmp -s $O/argmax_mut.sv $AM && { echo "HGI_ARGMAX FAIL mutant-not-applied"; exit 2; }
      AM=$O/argmax_mut.sv; D=""
    fi
    S="rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv
       $AM $G/tb/tb_hgi_argmax.sv"; TOP=tb_hgi_argmax; TAG=HGI_ARGMAX; RUNDIR=.
    [ $B = argmax_f1 ] && D="$D -Ptb_hgi_argmax.FAST=1";;
  seq)
    S="$G/ot_hgi_seq.sv $G/tb/tb_hgi_seq.sv"; TOP=tb_hgi_seq; TAG=HGI_SEQ; RUNDIR=$G/tb;;
  *) echo "unknown bench $B"; exit 2;;
esac
iverilog -g2012 $D -I $G -I $G/tb -o $O/$B.vvp -s $TOP $S > $O/$B.build.log 2>&1 || { echo "$TAG FAIL build"; head -20 $O/$B.build.log; exit 2; }
(cd $RUNDIR && vvp -n $OLDPWD/$O/$B.vvp) > $O/$B.log 2>&1
L=$(grep -m1 "^$TAG " $O/$B.log || echo "$TAG FAIL no-summary")
echo "$L"; grep -m5 "FAIL\|MISMATCH" $O/$B.log | head -5
case "$L" in "$TAG PASS"*) exit 0;; *) exit 1;; esac
