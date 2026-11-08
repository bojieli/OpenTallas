#!/bin/bash
# QC-TYPES-10/CTLM: HP13 die-form head bench (TOKc-SEGCAL run_segcal_bench.sh die runs) on base / FQREG / FQREG-mutant u_cal
set -u; H=$(readlink -f "$1"); cd $H
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
IMG=$H/ref/results/rtl/qlb_c4b_1018/lmh_cal/codex_r1; BENCH=$H/ref/rtl/test/qwen_dv/tt_ctlm_prog_bench.py; O=$H/runs; mkdir -p $O
A=(--decode 3 --hard 1)
die() { local dut=$1; shift; python3 $H/hp13_prog_bench.py --bench $BENCH --root $H/$dut --tb $H/tb_qfd_tt_ctlm_prog_hp13.sv --sources $H/$dut/hp13_sources.f "$@"; }
( die dut_base --lockstep -- "${A[@]}" --segcal 1 --img $IMG/imgh --work $O/base_imgh > $O/base_imgh.out 2>&1; echo "RC $?" >> $O/base_imgh.out ) &
( die dut_fqreg --lockstep -- "${A[@]}" --segcal 1 --img $IMG/imgh --work $O/fq_imgh > $O/fq_imgh.out 2>&1; echo "RC $?" >> $O/fq_imgh.out
  die dut_fqreg --lockstep -- "${A[@]}" --segcal 1 --bmut 3 --img $IMG/imgh --work $O/fq_imgh > $O/fq_bmut3.out 2>&1; echo "RC $?" >> $O/fq_bmut3.out ) &
( die dut_fqreg --lockstep -- "${A[@]}" --segcal 1 --img $IMG/img0 --work $O/fq_img0 > $O/fq_img0.out 2>&1; echo "RC $?" >> $O/fq_img0.out ) &
( die dut_fqreg_mut2 --lockstep -- "${A[@]}" --segcal 1 --img $IMG/imgh --work $O/fqm2_imgh > $O/fqm2_imgh.out 2>&1; echo "RC $?" >> $O/fqm2_imgh.out ) &
wait
for f in $O/*.out; do echo "$(basename $f .out): $(grep -E 'CTLM_PROG|LANDED_LOCKSTEP|^RC' $f | tr '\n' ' ')"; done | tee $O/summary.txt
