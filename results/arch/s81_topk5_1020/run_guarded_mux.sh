#!/bin/bash
set -euo pipefail
O=${1:?output};M=${2:-0};mkdir -p "$O"
verilator --binary --timing --top-module tb_guarded_mux -Wno-fatal -j 4 \
  --Mdir "$O/obj" -GMUT="$M" \
  rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_guarded_mux.sv \
  results/arch/s81_topk5_1020/tb_guarded_mux.sv > "$O/build.log" 2>&1
set +e
"$O/obj/Vtb_guarded_mux" > "$O/run.log" 2>&1
rc=$?
set -e
if [[ "$M" == 0 ]];then
  [[ "$rc" == 0 ]] && grep -q 'GUARDED_MUX PASS MUT=0' "$O/run.log"
else
  [[ "$rc" != 0 ]] && grep -q "GUARDED_MUX FAIL MUT=$M" "$O/run.log" && ! grep -q 'GUARDED_MUX PASS' "$O/run.log"
fi
