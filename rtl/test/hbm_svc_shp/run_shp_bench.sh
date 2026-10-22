#!/bin/bash
# kshare r5a shared-pointer FIFO lockstep vs the reviewed FIFO.  usage: OUT ; exit 0 iff all positives PASS and MUT 1 FAILs
set -u; cd "$(dirname "$0")/../../.."; OUT=$(realpath -m "$1"); mkdir -p "$OUT"; rc=0
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S="rtl/lib/ot_reset_sync.sv rtl/lib/ot_rst_fanout.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo_shp.sv rtl/test/hbm_svc_shp/tb_svc_async_fifo_shp.sv"
run(){ n=$1; shift; rm -f "$OUT/$n.log"; "$VL" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_svc_async_fifo_shp "$@" $S --Mdir "$OUT/o_$n" -o v >"$OUT/b_$n.log" 2>&1 && "$OUT/o_$n/v" >"$OUT/$n.log" 2>&1; grep -h "SHP_LOCKSTEP\|SHP_INVARIANT" "$OUT/$n.log" | sed "s/^/$n: /"; }
for cfg in "fill8 -GWIDTH=279 -GDEPTH=8 -GSW=7" "fill8s3 -GWIDTH=279 -GDEPTH=8 -GSW=3 -GSEED=5" "cmd4 -GWIDTH=36 -GDEPTH=4 -GSW=5 -GSEED=7" "wq4 -GWIDTH=105 -GDEPTH=4 -GSW=5 -GSEED=9" "w1 -GWIDTH=1 -GDEPTH=8 -GSW=7 -GSEED=3"; do
 set -- $cfg; n=$1; shift; out=$(run $n "$@"); echo "$out"; echo "$out" | grep -q "PASS" || rc=1; done
out=$(run mut1 -GWIDTH=279 -GDEPTH=8 -GSW=7 -GMUT=1); echo "$out"; echo "$out" | grep -q "FAIL" || rc=1
out=$(run mut_RS_TWICE -GWIDTH=279 -GDEPTH=8 -GSW=7 -DOT_SHP_MUT_RS_TWICE); echo "$out"; echo "$out" | grep -q "FAIL" || rc=1
out=$(run mut_RS_DEEPc -GWIDTH=279 -GDEPTH=8 -GSW=7 -DOT_SHP_MUT_RS_DEEP); echo "$out" | grep -q "FAIL" && echo "RS_DEEP CAUGHT" || { echo "RS_DEEP NOT CAUGHT"; rc=1; }
# review 10:45 (b): group reset syncs one stage deeper / main syncs one stage deeper (reported; static check in the tool)
for m in RS_DEEP; do out=$(run mut_$m -GWIDTH=279 -GDEPTH=8 -GSW=7 -DOT_SHP_MUT_$m); echo "$out"; grep -h "SHP_INVARIANT" "$OUT/mut_$m.log" | sed "s/^/mut_$m: /"; done
echo "SHP_BENCH_EXIT $rc"; exit $rc
