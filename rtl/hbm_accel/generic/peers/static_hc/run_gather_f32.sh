#!/bin/bash
# HBM-HCBANK6 10-20: tb_hc_gather_f32 (native32 gathered reader vs the RSC 24 reader), Verilator 5.050.
# Usage: run_gather_f32.sh OUT [MUT]   MUT 0 -> "GATHER_F32 PASS MUT=0", MUT 1 -> "GATHER_F32 FAIL MUT=1"
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:-0}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc
"$vl" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hc_gather_f32 +define+MUT=$mut -Mdir "$out/obj" -o Vg \
  rtl/test/tb_hc_gather_f32.sv $H/ot_hgi_hc_gathered_mix_reader_static.sv $H/ot_hgi_hc_gathered_mix_reader_f32_static.sv > "$out/build.log" 2>&1
set +e; "$out/obj/Vg" > "$out/run.log" 2>&1; set -e
grep -E "GATHER_F32|MISMATCH" "$out/run.log" | head -6
"$vl" --version
rm -rf "$out/obj"
grep -q "GATHER_F32 PASS" "$out/run.log"
