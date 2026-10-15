#!/usr/bin/env bash
set -euo pipefail
out=${1:?fresh output directory}; mut=${2:-0}; mkdir -p "$out"
flags=(); if [[ $mut == 1 ]]; then flags+=(-DOT_SLICE_DIE_MUT); elif [[ $mut == 2 ]]; then flags+=(-DOT_SLICE_BOOT_MUT); fi
src=(rtl/qwen_sys/split_20261014/qkd_host_pc_slice_die.sv rtl/qwen_sys/split_20261014/qkd_host_pc_slice.sv rtl/qwen_sys/host_20261013/qkd_host_ingest_station.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc_emback.sv rtl/qwen_sys/split_20261014/qkd_hbm_boot_static_completion.sv rtl/qwen_sys/split_20261014/qkd_hbm_boot_static.sv rtl/qwen_sys/split_20261014/qkd_hbm_boot_pc.sv rtl/qwen_sys/split_20261014/qkd_static_completion_ownerdemux.sv)
iverilog -g2012 -s tb_host_pc_slice_die_pin_capture "${flags[@]}" -o "$out/sim.vvp" rtl/test/qwen_split/tb_host_pc_slice_die_pin_capture.sv "${src[@]}" > "$out/build.log" 2>&1
vvp "$out/sim.vvp" | tee "$out/result.log"
