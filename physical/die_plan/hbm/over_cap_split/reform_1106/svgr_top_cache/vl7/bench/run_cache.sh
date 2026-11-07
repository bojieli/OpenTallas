#!/bin/bash
# DIE-HBM-87 vL7 cache lock-step bench (iverilog 12, host tools).
# run_cache.sh REF_CACHE DUT_CACHE WORKDIR : REF = the vL6 kit ot_svgr_cache136_native.sv (sha256 f913722a...), DUT = vL7 source.
# Matrix: off / WDEC / GSEL(GREP 1,2) / combined (GREP 2,4) / combined WPIPE 0, seeds 1-3, NCYC (default 200000) each.
set -u; R=$1; D=$2; W=$3; H=$(cd "$(dirname "$0")" && pwd); cd /
N=${NCYC:-200000}; mkdir -p $W/logs
sed -e 's/\bmodule ot_svgr_cache136_native\b/module ot_svgr_cache136_native_ref/' $R > $W/ref_cache.sv; cp $D $W/dut.sv
run(){ t=$1; shift; iverilog -g2012 "$@" -o $W/bin_$t $H/tb_cache_ls.sv $W/ref_cache.sv $W/dut.sv $H/sram_beh.sv >$W/logs/$t.comp 2>&1 && vvp -n $W/bin_$t >$W/logs/$t.log 2>&1; rm -f $W/bin_$t; }
for s in 1 2 3; do
 for c in "off:0:0:1:1" "wdec:1:0:1:1" "gsel1:0:1:1:1" "gsel2:0:1:2:1" "comb:1:1:2:1" "comb4:1:1:4:1" "comb_wp0:1:1:2:0"; do
  IFS=: read n w g r wp <<<"$c"; run ${n}_s$s -DNCYC=$N -DSEED=$s -DWDEC=$w -DGS=$g -DGR=$r -DWP=$wp &
 done
done
wait; grep -h '^RESULT' $W/logs/*.log
