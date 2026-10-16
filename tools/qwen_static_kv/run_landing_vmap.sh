#!/bin/bash
# run_landing_vmap.sh OUT: tb_static_landing (32 groups / 128 PCs / ctx 8192, real SRAM model) for the historical V
# layout (VMAP 0), the PV16 layout (VMAP 1, w16 pair walk), and negatives (fault modes 1-4 under VMAP 1; a VMAP 0 DUT
# fed the PV16 layout).  Prints one RESULT line per case; exit 0 iff every case meets its expectation.
set -u
O=$1;mkdir -p "$O";VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/qwen_sys/static_kv_20261014
build(){ $VL --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTH -Wno-MULTIDRIVEN --build-jobs 8 \
  --top-module tb_static_landing -GVMAP=$1 -GDUT_VMAP=$2 --Mdir "$O/obj_$1_$2" \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  $S/qkd_static_kv_landing.sv rtl/test/qwen_static_kv/tb_static_landing.sv > "$O/build_$1_$2.log" 2>&1 || { echo "RESULT FAIL build $1 $2"; tail -5 "$O/build_$1_$2.log"; return 1; }; }
rc=0
run(){ # vmap dut_vmap faultmode expect
 l=$("$O/obj_$1_$2/Vtb_static_landing" +faultmode=$3 2>&1 | grep -E "^(PASS|FAIL) staticlanding" | tail -1)
 case "$l" in PASS*) got=pass;; FAIL*) got=fail;; *) got=noresult;; esac   # a run without a result line never counts as an expected FAIL
 [ "$got" = "$4" ] && ok=OK || { ok=UNEXPECTED; rc=1; }
 echo "RESULT $ok vmap=$1 dut_vmap=$2 faultmode=$3 expect=$4 :: ${l:-no result line}"; }
build 0 0 && run 0 0 0 pass
build 1 1 && { run 1 1 0 pass; for f in 1 2 3 4; do run 1 1 $f fail; done; }
build 1 0 && run 1 0 0 fail
exit $rc
