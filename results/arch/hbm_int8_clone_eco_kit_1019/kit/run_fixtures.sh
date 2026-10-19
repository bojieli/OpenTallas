#!/bin/bash
# Fleet-only, granted campaign; preserve all incremental outputs and fail witnesses.
set -euo pipefail
kit=$(cd "$(dirname "$0")" && pwd)
: "${INT8_FIXTURE_OUTPUT:?isolated output path required}"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q 'Verilator 5.050'
f="$kit/fixtures"
mkdir -p "$INT8_FIXTURE_OUTPUT"
for top in tb_smh_int8_tile_safe tb_smh_int8_tile_safe_truth tb_smh_int8_tile_safe_reset; do
 out="$INT8_FIXTURE_OUTPUT/$top";mkdir -p "$out"
 verilator --binary --timing -j 2 -Wno-fatal --top-module "$top" --Mdir "$out/obj" -o tb "$f/$top.sv" "$f/ot_smh_int8_tile.sv" "$f/ot_smh_int8_tile_safe.sv" "$f/ot_smh_static_int8.sv" "$f/ot_hbm_accel_int8_line.sv" > "$out/build.log" 2>&1
 "$out/obj/tb" > "$out/run.log" 2>&1
 grep -E 'I8T (PASS|TRUTH PASS|RESET PASS)' "$out/run.log"
done
python3 - "$f" "$INT8_FIXTURE_OUTPUT" <<'PY'
import pathlib,sys
f,o=map(pathlib.Path,sys.argv[1:]);s=(f/'ot_smh_int8_tile_safe.sv').read_text();assert s.count('reset_final <= {9{reset_first}};')==1
(o/'reset_short.sv').write_text(s.replace('reset_final <= {9{reset_first}};','reset_final <= {9{rst_n}};'))
(o/'reset_long.sv').write_text(s.replace('(* keep *) reg reset_first;','(* keep *) reg reset_first; reg reset_middle; always @(posedge clk) reset_middle<=reset_first;').replace('reset_final <= {9{reset_first}};','reset_final <= {9{reset_middle}};'))
PY
for mutant in short long; do
 out="$INT8_FIXTURE_OUTPUT/reset_$mutant";mkdir -p "$out"
 verilator --binary --timing -j 2 -Wno-fatal --top-module tb_smh_int8_tile_safe_reset --Mdir "$out/obj" -o tb "$f/tb_smh_int8_tile_safe_reset.sv" "$f/ot_smh_int8_tile.sv" "$INT8_FIXTURE_OUTPUT/reset_$mutant.sv" > "$out/build.log" 2>&1
 if "$out/obj/tb" > "$out/run.log" 2>&1; then echo "UNCAUGHT_RESET_MUTANT $mutant";exit 1;fi
 grep -E 'RESET (LOCKSTEP|STAGE) FAIL' "$out/run.log"
done
