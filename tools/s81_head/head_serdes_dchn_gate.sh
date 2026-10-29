#!/usr/bin/env bash
set -eu
task_run=${1:?fresh output directory}
mkdir -p "$task_run"
task_root=$(cd "$(dirname "$0")/../.." && pwd)
task_link=$task_root/rtl/dsrom_sys/s81_link
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style \
  --top-module tb_head_serdes_dchn +incdir+"$task_link" \
  --Mdir "$task_run/obj" -o tb \
  "$task_link/ot_s81_kp4_common.sv" "$task_link/ot_s81_kp4_dchn.sv" \
  "$task_root/rtl/dsrom_sys/s81_head/tb_head_serdes_dchn.sv" > "$task_run/build.log" 2>&1
"$task_run/obj/tb" > "$task_run/run.log" 2>&1
grep '^HEAD_DCHN PASS' "$task_run/run.log"
