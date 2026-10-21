#!/bin/bash
# HBM-HCBANK6 10-20: ot_static_program_target FAN32 1 vs FAN32 0 lockstep (tb_static_program_target_fan32), Verilator 5.050.
# Usage: run_ptgt_fan32.sh OUT [MUT]   MUT 0 -> "PTGT_FAN32 PASS MUT=0", MUT 1 (no pending-write bypass) -> "PTGT_FAN32 FAIL MUT=1"
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:-0}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
"$vl" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_static_program_target_fan32 +define+MUT=$mut \
  -Mdir "$out/obj" -o Vpt rtl/test/tb_static_program_target_fan32.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv > "$out/build.log" 2>&1
set +e; "$out/obj/Vpt" > "$out/run.log" 2>&1; set -e
grep -E "PTGT_FAN32|MISMATCH|FAULTRISE" "$out/run.log" | head -16
"$vl" --version
rm -rf "$out/obj"
grep -q "PTGT_FAN32 PASS" "$out/run.log"
