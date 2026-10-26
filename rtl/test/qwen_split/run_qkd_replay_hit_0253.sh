#!/bin/bash
set -eu
out=$1; mut=${2:-0}; mkdir -p "$out"
args=(); [ "$mut" = 0 ] || args+=(-DOT_QKD_REPLAY_HIT_MUT)
iverilog -g2012 -DOT_MEM_NO_INIT "${args[@]}" -s tb_qkd_replay_hit_0253 -o "$out/test.vvp" rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/test/qwen_split/qkd_replay_sram_prior_0253.sv rtl/test/qwen_split/tb_qkd_replay_hit_0253.sv > "$out/build.log" 2>&1
vvp -n "$out/test.vvp" > "$out/run.log" 2>&1
grep '^REPLAY_HIT_PASS' "$out/run.log"
