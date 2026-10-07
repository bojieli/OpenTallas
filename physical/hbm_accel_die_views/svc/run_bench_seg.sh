#!/bin/bash
# CLAUDE HBM-ABSTRACTS (svcidx): lint (per segment master) + exact bench of the SEGMENTED stream service (the segments
# joined, same bench as the one-slot views, SW and NE) + two negatives: assembler beat-order mutant and a cross-bus
# lane swap in the joined SW top (both must FAIL).   run_bench_seg.sh <out dir>   (run from the source snapshot root)
set -u
O=$1; mkdir -p $O; V=physical/hbm_accel_die_views/svc
SRC="rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv $V/rtl/ot_hbm_svc_core.sv $V/rtl/ot_hbm_svc_seg_lib.sv"
rc=0
for f in $V/rtl/seg/hfd_svc_S[WE]_s[0-9].sv; do
  m=$(basename $f .sv)
  docker run --rm -v $PWD:/s:ro -w /s openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -p \
    "read_verilog -sv $SRC $f; hierarchy -check -top $m; proc; flatten; opt_clean; check -assert" > $O/lint_$m.log 2>&1
  r=$?; echo "lint_$m rc=$r" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
done
sim() {   # sim <label> <st> <fam> <core file> <joined top file>
  sed "s/hfd_svc_$2 dut/hfd_svc_$2_seg dut/" $V/tb/tb_hfd_svc_$2.sv > $O/tb_$1.sv
  iverilog -g2012 -o $O/$1.vvp -I $V/tb -s tb_hfd_svc_$2 rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv $4 $V/rtl/ot_hbm_svc_seg_lib.sv \
    $V/rtl/seg/hfd_svc_$3_s[0-9].sv $5 $V/tb/tb_svc_physide.sv $O/tb_$1.sv > $O/build_$1.log 2>&1
  vvp -n $O/$1.vvp > $O/$1.log 2>&1
}
for st in SW:SW NE:SE; do
  s=${st%:*}; f=${st#*:}
  sim sim_$s $s $f $V/rtl/ot_hbm_svc_core.sv $V/rtl/seg/hfd_svc_${s}_seg.sv; r=$?
  echo "sim_$s rc=$r $(grep SVC_BENCH $O/sim_$s.log | tail -1)" >> $O/summary.txt; [ $r -ne 0 ] && rc=1
done
sed 's/b\[bbeat\] <= bdata/b[bbeat ^ 5'"'"'d1] <= bdata/' $V/rtl/ot_hbm_svc_core.sv > $O/core_mutant.sv
cmp -s $O/core_mutant.sv $V/rtl/ot_hbm_svc_core.sv && { echo "mutant not applied" >> $O/summary.txt; rc=1; }
sim neg_beat SW SW $O/core_mutant.sv $V/rtl/seg/hfd_svc_SW_seg.sv; r=$?
echo "neg_beat rc=$r (must be nonzero) $(grep SVC_BENCH $O/neg_beat.log | tail -1)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
# cross-bus mutant: the eastward bus of cut 0 one data bit inverted (bit 6) between segment 0 and segment 1
sed 's/\.wi(xr0)/.wi(xr0 ^ 64)/' $V/rtl/seg/hfd_svc_SW_seg.sv > $O/seg_mutant.sv
cmp -s $O/seg_mutant.sv $V/rtl/seg/hfd_svc_SW_seg.sv && { echo "cross mutant not applied" >> $O/summary.txt; rc=1; }
sim neg_cross SW SW $V/rtl/ot_hbm_svc_core.sv $O/seg_mutant.sv; r=$?
echo "neg_cross rc=$r (must be nonzero) $(grep SVC_BENCH $O/neg_cross.log | tail -1)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1
echo "overall rc=$rc" >> $O/summary.txt; exit $rc
