#!/bin/bash
# Verilator 5.050 (the closure daemon's pinned version) bench of the selector: same stimulus/checks as run_selector.sh.
# Usage: run_selector_vl.sh OUT MUT SHELL   (MUT 0 must pass; MUT 1 ties, 2 emitted id, 3 lane-5 write-data select copy one
# edge late, 4 lane-3 emit copy one edge early must FAIL with "fullshape exact selector mismatch"; SHELL=1 = die master)
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-static-selector-vl}")
m=${2:-0}; shell=${3:-1}
mkdir -p "$out"
python3 tools/hbm_idx_static_selector_vectors.py "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x "$vl" ]||vl=verilator
"$vl" --version
"$vl" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_selector_static \
 -GMUT="$m" -GSHELL="$shell" -Mdir "$out/obj$m" \
 rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv rtl/lib/ot_rst_relay.sv rtl/test/hbm_idx_static/tb_selector_static.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v > "$out/vbuild$m.log" 2>&1 || { tail -40 "$out/vbuild$m.log"; exit 3; }
set +e
(cd "$out" && "$out/obj$m/Vtb_selector_static") > "$out/vrun$m.log" 2>&1
rc=$?
set -e
cat "$out/vrun$m.log"
exit "$rc"
