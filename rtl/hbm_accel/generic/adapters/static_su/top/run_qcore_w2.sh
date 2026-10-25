#!/usr/bin/env bash
# HBM-BIND B2 (2026-10-24): ot_hbm_su_static_qcore_r13_w2 gate (Verilator 5.050, --binary): MUTW 0 PASS vs the as-built
# 4-writer core bound as on the 16-SM die (writers 2 / 3), MUTW 1 (swapped writers) FAIL.   run_qcore_w2.sh OUT [NCYC]
set -uo pipefail
out=$(realpath -m "${1:?out}"); NCYC=${2:-20000}; mkdir -p "$out"; d=$(cd "$(dirname "$0")" && pwd); r=$(cd "$d/../../../../../.." && pwd); fail=0
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
# the core's reducer / pretree / FP leaves are found by module name (-y library search)
Y="-y $d -y $d/../reduction -y $r/rtl/lib -y $r/rtl/hdc $r/rtl/hdc/ot_hdc_prefix.sv $d/../reduction/ot_hbm_su_red_pretree_r13.sv
   $r/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
for m in 0 1; do
 "$V" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-UNOPTFLAT -Wno-MULTIDRIVEN --top-module tb_hbm_su_qcore_w2 \
   -GMUTW=$m -GNCYC=$NCYC --Mdir "$out/m$m" -o tb $Y "$d/tb_hbm_su_qcore_w2.sv" "$d/ot_hbm_su_static_qcore_r13_w2.sv" \
   "$d/ot_hbm_su_static_qcore_r13.sv" > "$out/build_$m.log" 2>&1 || { echo "BUILD_FAIL MUTW=$m"; tail -20 "$out/build_$m.log"; exit 2; }
 "$out/m$m/tb" +verilator+seed+11 > "$out/run_$m.log" 2>&1; r1=$(grep -E '^QCORE_W2' "$out/run_$m.log"); echo "MUTW=$m $r1"
 if [ $m = 0 ]; then echo "$r1" | grep -q ' PASS ' || fail=1; else echo "$r1" | grep -Eq ' FAIL checks=[0-9]+ errors=[1-9]' || fail=1; fi
 rm -rf "$out/m$m"
done
[ $fail = 0 ] && echo "QCORE_W2_GATE PASS" || { echo "QCORE_W2_GATE FAIL"; exit 1; }
