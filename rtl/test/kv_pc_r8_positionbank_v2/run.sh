#!/bin/bash
set -euo pipefail
OUT=$(realpath -m "${1:?out}");mkdir -p "$OUT"
for m in 0 1;do
 verilator --binary --timing -Wno-fatal --top-module tb_v2 -GMUT=$m rtl/physical/kv_pc_r8_position_bank_v2.sv rtl/test/kv_pc_r8_positionbank_v2/tb_v2.sv --Mdir "$OUT/obj$m" -o tb > "$OUT/build$m.log" 2>&1
 if "$OUT/obj$m/tb" > "$OUT/run$m.log" 2>&1;then rc=0;else rc=$?;fi
 if [ $m = 0 ];then test "$rc" = 0;grep 'POS_V2 PASS' "$OUT/run$m.log";else test "$rc" != 0;grep 'POS_V2 FAIL' "$OUT/run$m.log";echo 'POS_V2 wrong-position-decode mutant CAUGHT';fi
done
