#!/bin/bash
# HBM-HCBANK6 10-20: tb_hbm_hc_qtree16 (hard tree slice vs the SAFE 1 subtree) on Verilator 5.050.
# Usage: run_qtree16.sh OUT [MUT]   MUT 0 -> "QTREE16 PASS MUT=0", MUT 4 -> "QTREE16 FAIL MUT=4"
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:-0}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
python3 tools/prepare_fp32_fan32_models.py --out "$out/cells.v"
"$vl" --binary --timing -j "${HC_BUILD_JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_hc_qtree16 +define+MUT=$mut \
  -Mdir "$out/obj" -o Vqt rtl/test/tb_hbm_hc_qtree16.sv rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_qtree16_static.sv \
  rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v "$out/cells.v" rtl/hdc/ot_hdc_fp32_add_lat.sv \
  rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/lib/ot_rst_relay.sv > "$out/build.log" 2>&1
set +e; "$out/obj/Vqt" > "$out/run.log" 2>&1; rc=$?; set -e
# Always expose the terminal verdict to the closure daemon's committed regex.
# Mismatch detail is bounded independently so it cannot displace the verdict.
grep -E '^QTREE16 (PASS|FAIL)' "$out/run.log"
grep -m 6 '^MISMATCH' "$out/run.log" || true
"$vl" --version
rm -rf "$out/obj"
grep -q "QTREE16 PASS" "$out/run.log"
