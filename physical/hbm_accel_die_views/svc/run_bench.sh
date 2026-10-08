#!/bin/bash
# CLAUDE HBM-ABSTRACTS (svcidx): lint + bench of the stream-service die views (one seed per top, + mutant negative)
#   run_bench.sh <out dir>        (run from the source snapshot root)
set -u
O=$1; mkdir -p $O; V=physical/hbm_accel_die_views/svc
SRC="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv $V/rtl/ot_hbm_svc_core.sv $V/rtl/ot_hbm_svc_phybind.sv"
rc=0
for st in SW SE NW NE; do
  # connectivity lint: yosys hierarchy -check + check -assert (undriven / multiply driven / unconnected cells)
  docker run --rm -v $PWD:/s:ro -w /s openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -p \
    "read_verilog -sv $SRC $V/rtl/hfd_svc_$st.sv; hierarchy -check -top hfd_svc_$st; proc; flatten; opt_clean; check -assert" \
    > $O/lint_$st.log 2>&1; r=$?; echo "lint_$st rc=$r" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
done
for st in SW NE; do
  iverilog -g2012 -o $O/sim_$st.vvp -I $V/tb -s tb_hfd_svc_$st $SRC $V/rtl/hfd_svc_$st.sv $V/tb/tb_svc_physide.sv $V/tb/tb_hfd_svc_$st.sv > $O/build_$st.log 2>&1
  vvp -n $O/sim_$st.vvp > $O/sim_$st.log 2>&1; r=$?; echo "sim_$st rc=$r $(grep SVC_BENCH $O/sim_$st.log | tail -1)" >> $O/summary.txt
  [ $r -ne 0 ] && rc=1
done
# negative control: beat-order mutant of the assembler (temporary copy; the source is unchanged)
sed 's/b\[bbeat\] <= bdata/b[bbeat ^ 5'"'"'d1] <= bdata/' $V/rtl/ot_hbm_svc_core.sv > $O/core_mutant.sv
cmp -s $O/core_mutant.sv $V/rtl/ot_hbm_svc_core.sv && { echo "mutant not applied" >> $O/summary.txt; rc=1; }
iverilog -g2012 -o $O/sim_neg.vvp -I $V/tb -s tb_hfd_svc_SW rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv $O/core_mutant.sv $V/rtl/ot_hbm_svc_phybind.sv $V/rtl/hfd_svc_SW.sv $V/tb/tb_svc_physide.sv $V/tb/tb_hfd_svc_SW.sv > $O/build_neg.log 2>&1
vvp -n $O/sim_neg.vvp > $O/sim_neg.log 2>&1; r=$?; echo "neg rc=$r (must be nonzero) $(grep SVC_BENCH $O/sim_neg.log | tail -1)" >> $O/summary.txt
[ $r -eq 0 ] && rc=1
echo "overall rc=$rc" >> $O/summary.txt
exit $rc
