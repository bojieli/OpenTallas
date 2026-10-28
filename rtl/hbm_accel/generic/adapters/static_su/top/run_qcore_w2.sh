#!/usr/bin/env bash
# HBM-BIND B2 (2026-10-24): ot_hbm_su_static_qcore_r13_w2 gate (iverilog): MUTW 0 PASS vs the as-built 4-writer core bound
# as on the 16-SM die (writers 2 / 3), MUTW 1 (swapped writers) FAIL.   run_qcore_w2.sh OUT
set -uo pipefail
out=$(realpath -m "${1:?out}"); mkdir -p "$out"; d=$(cd "$(dirname "$0")" && pwd); r=$(cd "$d/../../../../../.." && pwd); fail=0
# the core's reducer / pretree / FP leaves are found by module name (iverilog library search)
Y="-Y .sv -Y .v -y $d -y $d/../reduction -y $r/rtl/lib -y $r/rtl/hdc $r/rtl/hdc/ot_hdc_prefix.sv $d/../reduction/ot_hbm_su_red_pretree_r13.sv
   $r/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
for m in 0 1; do
 iverilog -g2012 $Y -Ptb_hbm_su_qcore_w2.MUTW=$m -o "$out/s_$m" -s tb_hbm_su_qcore_w2 "$d/tb_hbm_su_qcore_w2.sv" \
  "$d/ot_hbm_su_static_qcore_r13_w2.sv" "$d/ot_hbm_su_static_qcore_r13.sv" > "$out/build_$m.log" 2>&1 \
  || { echo "BUILD_FAIL MUTW=$m"; tail -20 "$out/build_$m.log"; exit 2; }
 vvp -n "$out/s_$m" > "$out/run_$m.log"; r=$(grep -E '^QCORE_W2' "$out/run_$m.log"); echo "MUTW=$m $r"
 if [ $m = 0 ]; then echo "$r" | grep -q ' PASS ' || fail=1; else echo "$r" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
done
[ $fail = 0 ] && echo "QCORE_W2_GATE PASS" || { echo "QCORE_W2_GATE FAIL"; exit 1; }
