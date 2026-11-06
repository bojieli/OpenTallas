#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-hbm-su-opf4-1106
variant=$1
base=/srv/opentallas-scratch2/claude/hbm-bind-6/tip2
$HOME/.local/opentallas-tools/bin/verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_su_static_lane_leaf --Mdir "$PWD/obj_indirect_$variant" "$PWD/tb_indirect.sv" "$PWD/rtl_$variant"/*.sv "$base/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11/sram_bench_model.sv" > build_indirect_$variant.log 2>&1
./obj_indirect_$variant/Vtb_su_static_lane_leaf +DIR="$PWD/vec_indirect" > indirect_$variant.log 2>&1
tail -5 indirect_$variant.log
