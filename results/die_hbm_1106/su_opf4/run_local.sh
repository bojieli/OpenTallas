#!/usr/bin/env bash
set -euo pipefail
phase_root=/srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106
baseline_root=/srv/opentallas-scratch2/claude/hbm-bind-6/tip2
variant=$1
cd "$phase_root"
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_su_static_lane_leaf --Mdir "$phase_root/obj_local_$variant" "$phase_root/tb_local_enable.sv" "$phase_root/rtl_$variant"/*.sv "$baseline_root/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11/sram_bench_model.sv" > "$phase_root/build_local_$variant.log" 2>&1
set +e
"$phase_root/obj_local_$variant/Vtb_su_static_lane_leaf" +DIR="$phase_root/vec" > "$phase_root/local_$variant.log" 2>&1
rc=$?
set -e
cat "$phase_root/local_$variant.log"
if [ "$variant" != positive ]; then test "$rc" -ne 0; exit $?; fi
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
set +e
"$phase_root/obj_local_$variant/Vtb_su_static_lane_leaf" +DIR="$phase_root/vec" +MUT_DATA > "$phase_root/local_field_mutant.log" 2>&1
rc=$?
set -e
test "$rc" -ne 0
