#!/bin/bash
# CLAUDE HBM-ABSTRACTS (svcidx): lint (per band) + exact bench of the SEGMENTED index quarter (six bands joined,
# hfd_index_q_seg, same bench as the one-slot view) + lane-swap mutant negative.   run_bench_split.sh <out dir>
set -u
O=$1; mkdir -p $O; V=physical/hbm_accel_die_views/index_q
LIB="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv"
B="$V/rtl/split/hfd_index_q_b0.sv $V/rtl/split/hfd_index_q_b1.sv $V/rtl/split/hfd_index_q_b2.sv $V/rtl/split/hfd_index_q_b3.sv $V/rtl/split/hfd_index_q_b4.sv $V/rtl/split/hfd_index_q_b5.sv"
rc=0
for b in 0 1 2 3 4 5; do
  docker run --rm -v $PWD:/s:ro -w /s openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -p \
    "read_verilog -sv $LIB $V/rtl/split/hfd_index_q_b$b.sv; hierarchy -check -top hfd_index_q_b$b; proc; flatten; opt_clean; check -assert" > $O/lint_b$b.log 2>&1
  r=$?; echo "lint_b$b rc=$r" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
done
sed 's/hfd_index_q dut/hfd_index_q_seg dut/' $V/tb/tb_hfd_index_q.sv > $O/tb_seg.sv
grep -q "hfd_index_q_seg dut" $O/tb_seg.sv || { echo "tb not retargeted" >> $O/summary.txt; rc=1; }
iverilog -g2012 -o $O/sim.vvp -s tb_hfd_index_q $LIB $B $V/rtl/split/hfd_index_q_seg.sv $O/tb_seg.sv > $O/build.log 2>&1
vvp -n $O/sim.vvp > $O/sim.log 2>&1; r=$?; echo "sim_seg rc=$r $(grep IDXQ_BENCH $O/sim.log | tail -1)" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
sed 's/pick1 ? fd\[2\*g+1\] : fd\[2\*g\]/pick1 ? fd[2*g] : fd[2*g+1]/' $V/rtl/split/hfd_index_q_b2.sv > $O/b2_mutant.sv
cmp -s $O/b2_mutant.sv $V/rtl/split/hfd_index_q_b2.sv && { echo "mutant not applied" >> $O/summary.txt; rc=1; }
BN=$(echo $B | sed "s#$V/rtl/split/hfd_index_q_b2.sv#$O/b2_mutant.sv#")
iverilog -g2012 -o $O/neg.vvp -s tb_hfd_index_q $LIB $BN $V/rtl/split/hfd_index_q_seg.sv $O/tb_seg.sv > $O/build_neg.log 2>&1
vvp -n $O/neg.vvp > $O/neg.log 2>&1; r=$?; echo "neg rc=$r (must be nonzero) $(grep IDXQ_BENCH $O/neg.log | tail -1)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
echo "overall rc=$rc" >> $O/summary.txt; exit $rc
