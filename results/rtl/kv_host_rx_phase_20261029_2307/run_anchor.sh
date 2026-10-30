#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-kvtok-2249
K=/srv/opentallas-scratch2/claude/tok-kv-1-1028/veh5/src/__srv__opentallas-scratch2__claude__wt__die-kv-16__physical__die_plan__qwen_kvsys__dcal_rom__bind__position2144b19/qkd_d2d_cal_seq_bc4_rom64.sv
S=/srv/opentallas-scratch2/claude/codex-qwen-token-1028/native_b5_start1/src
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_seq_anchor --Mdir $D/anchor_obj $D/tb_seq_anchor.sv $K $S/close__rtl__qwen_sys__d2d_static_20261015/ot_qwen_d2d_cal_seq_rom64_core.sv $S/close__rtl__qwen_sys__d2d_static_20261015/ot_qwen_d2d_cal_seq.sv $S/close__physical__asap7_memory_macros_v2__ot_rom_64x32_m2/ot_rom_64x32_m2.v >$D/anchor_build.log 2>&1
$D/anchor_obj/Vtb_seq_anchor >$D/anchor_run.log 2>&1
cat $D/anchor_run.log
