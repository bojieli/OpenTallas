#!/bin/bash
# CLAUDE HBM-ABSTRACTS (svcidx): lint + bench of the interim index-quarter view (+ lane-swap mutant negative)
set -u
O=$1; mkdir -p $O; V=physical/hbm_accel_die_views/index_q
SRC="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv $V/rtl/hfd_index_q.sv"
rc=0
docker run --rm -v $PWD:/s:ro -w /s openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -p \
  "read_verilog -sv $SRC; hierarchy -check -top hfd_index_q; proc; flatten; opt_clean; check -assert" > $O/lint.log 2>&1
r=$?; echo "lint rc=$r" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
iverilog -g2012 -o $O/sim.vvp -s tb_hfd_index_q $SRC $V/tb/tb_hfd_index_q.sv > $O/build.log 2>&1
vvp -n $O/sim.vvp > $O/sim.log 2>&1; r=$?; echo "sim rc=$r $(grep IDXQ_BENCH $O/sim.log | tail -1)" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
sed 's/pick1 ? fd\[2\*g+1\] : fd\[2\*g\]/pick1 ? fd[2*g] : fd[2*g+1]/' $V/rtl/hfd_index_q.sv > $O/mutant.sv
cmp -s $O/mutant.sv $V/rtl/hfd_index_q.sv && { echo "mutant not applied" >> $O/summary.txt; rc=1; }
iverilog -g2012 -o $O/neg.vvp -s tb_hfd_index_q rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv $O/mutant.sv $V/tb/tb_hfd_index_q.sv > $O/build_neg.log 2>&1
vvp -n $O/neg.vvp > $O/neg.log 2>&1; r=$?; echo "neg rc=$r (must be nonzero) $(grep IDXQ_BENCH $O/neg.log | tail -1)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
echo "overall rc=$rc" >> $O/summary.txt; exit $rc
