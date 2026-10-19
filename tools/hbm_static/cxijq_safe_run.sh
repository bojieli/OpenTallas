#!/bin/bash
set -euo pipefail
out=$1;mkdir -p "$out"
verilator --version
for pair in 0:0 2:0 0:5 0:6 0:4; do
 sd=${pair%:*};mut=${pair#*:};run="$out/sd${sd}_m${mut}";mkdir -p "$run"
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_hbm_cxijq_safe -GSD=$sd -GMUT=$mut --Mdir "$run/obj" -o sim rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv rtl/hbm_accel/generic/adapters/static_su/collport/tb_hbm_cxijq_safe.sv >"$run/build.log" 2>&1
 set +e
 "$run/obj/sim" >"$run/bench.log" 2>&1
 rc=$?
 set -e
 tail -4 "$run/bench.log"
 if [ "$mut" = 0 ]; then test "$rc" = 0;grep -q 'CXIJQ_SAFE PASS' "$run/bench.log";else test "$rc" != 0;grep -q 'CXIJQ_SAFE FAIL' "$run/bench.log";fi
 done
 echo MATRIX_PASS
