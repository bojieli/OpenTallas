#!/bin/bash
# run_cache_vm1.sh REF DUT WORK: vM1 cache WOH lock-step, ref vL7 kit cache (same params), seeds 1-3, kit params (WDEC1 GS1 GR2 WP1) + off-params
set -u; R=$1; D=$2; W=$3; H=$(cd "$(dirname "$0")" && pwd); cd /
N=${NCYC:-200000}; mkdir -p $W/logs
sed -e 's/\bmodule ot_svgr_cache136_native\b/module ot_svgr_cache136_native_ref/' $R > $W/ref_cache.sv; cp $D $W/dut.sv
run(){ t=$1; shift; iverilog -g2012 "$@" -o $W/bin_$t $H/tb_cache_ls.sv $W/ref_cache.sv $W/dut.sv $H/sram_beh.sv >$W/logs/$t.comp 2>&1 && vvp -n $W/bin_$t >$W/logs/$t.log 2>&1; rm -f $W/bin_$t; }
for s in 1 2 3; do
 for c in "kit:1:1:2:1:1" "kit_woh0:1:1:2:1:0" "wdec0:0:1:2:1:1" "gs0:1:0:1:1:1" "wp0:1:1:2:0:1"; do
  IFS=: read n w g r wp o <<<"$c"; run ${n}_s$s -DNCYC=$N -DSEED=$s -DWDEC=$w -DGS=$g -DGR=$r -DWP=$wp -DWOH=$o &
 done
done
wait; grep -h '^RESULT' $W/logs/*.log; grep -l -i error $W/logs/*.comp
