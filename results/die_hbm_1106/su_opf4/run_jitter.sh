#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106
baseline_root=/srv/opentallas-scratch2/claude/hbm-bind-6/tip2
"$HOME/.local/opentallas-tools/bin/verilator" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_su_static_lane_leaf --Mdir "$PWD/obj_jitter" "$PWD/tb_jitter.sv" "$PWD/rtl_positive"/*.sv "$baseline_root/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11/sram_bench_model.sv" > build_jitter.log 2>&1
./obj_jitter/Vtb_su_static_lane_leaf +DIR="$PWD/vec_jitter" > jitter.log 2>&1
./obj_jitter/Vtb_su_static_lane_leaf +DIR="$PWD/vec_jitter" +RESET_BETWEEN > jitter_reset.log 2>&1
tail -5 jitter.log
tail -5 jitter_reset.log
