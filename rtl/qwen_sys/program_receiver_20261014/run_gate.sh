#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
out=${1:?fresh output directory}
mkdir -p "$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
files=(rtl/qwen_sys/program_receiver_20261014/tb_qkd_program_commit.sv rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
cd "$root"
sha256sum "${files[@]}" > "$out/source.sha256"
"$v" --binary --timing -j 2 -O1 -Wno-fatal --top-module tb_qkd_program_commit --Mdir "$out/obj" "${files[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_qkd_program_commit" > "$out/macro_composition.log" 2>&1
cat "$out/macro_composition.log"
