#!/bin/bash
# run_mut.sh REF_CACHE DUT_CACHE WORKDIR : mutants.py mutants of DUT, combined form (WDEC 1, GSEL 1, GREP 2, WPIPE 1), seed 7,
# stop at the first port mismatch (caught) or NCYC (default 100000) edges (not caught).
set -u; R=$1; D=$2; W=$3; H=$(cd "$(dirname "$0")" && pwd); cd /
N=${NCYC:-100000}; mkdir -p $W/logs_mut
sed -e 's/\bmodule ot_svgr_cache136_native\b/module ot_svgr_cache136_native_ref/' $R > $W/ref_cache.sv
python3 -I $H/mutants.py $D $W/mut >/dev/null
for m in $W/mut/*.sv; do t=$(basename $m .sv)
 ( iverilog -g2012 -DSTOPMM -DNCYC=$N -DSEED=7 -DWDEC=1 -DGS=1 -DGR=2 -DWP=1 -o $W/mbin_$t $H/tb_cache_ls.sv $W/ref_cache.sv $m $H/sram_beh.sv >$W/logs_mut/$t.comp 2>&1 && vvp -n $W/mbin_$t >$W/logs_mut/$t.log 2>&1; rm -f $W/mbin_$t ) &
done
wait; for f in $W/logs_mut/*.log; do echo "$(basename $f .log) $(grep -h -E '^RESULT' $f)"; done
