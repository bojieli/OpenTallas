#!/bin/bash
set -euo pipefail
D=rtl/qwen_sys/d2d_static_20261015
O=/srv/opentallas-scratch/claude/qw-d2d-safe6u-1019/leaf
mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_qfd_sf6u_leaf --Mdir "$O/obj" "$D/ot_qwen_d2d_safe5.sv" "$D/ot_qwen_d2d_safe6u.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_64x137_m1_r2c2_p192/ot_sram_1r1w_64x137_m1_r2c2_p192.v rtl/test/qwen_split/tb_qfd_sf6u_leaf.sv > "$O/build.log" 2>&1
"$O/obj/Vtb_qfd_sf6u_leaf" > "$O/run.log" 2>&1
cat "$O/run.log"
