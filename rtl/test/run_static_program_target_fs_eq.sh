#!/bin/bash
# HBM-HCROOT6 10-20: ot_static_program_target_fs == ot_static_program_target edge for edge (Verilator 5.050).
# Usage: run_static_program_target_fs_eq.sh OUT [MUT] [N] [SEED]   (MUT 1 = fs bank 5 write dropped -> must FAIL)
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:-0}; n=${3:-200000}; seed=${4:-7}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
"$vl" --version
"$vl" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style --top-module tb_static_program_target_fs_eq +define+MUT=$mut \
  -Mdir "$out/obj" -o Vspt rtl/test/tb_static_program_target_fs_eq.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv \
  rtl/hbm_accel/generic/vm/static/ot_static_program_target_fs.sv > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; exit 1; }
set +e; "$out/obj/Vspt" +N=$n +SEED=$seed > "$out/run.log" 2>&1; rc=$?; set -e
grep -E "SPT_EQ|ERR" "$out/run.log" | head -12 || true
echo "SPT_EQ_RUN MUT=$mut N=$n SEED=$seed rc=$rc"
rm -rf "$out/obj"
