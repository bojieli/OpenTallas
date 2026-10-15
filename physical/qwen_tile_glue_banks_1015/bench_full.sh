#!/bin/bash
set -euo pipefail
out=$1
mut=${2:-0}
mkdir -p "$out"
iverilog -g2012 -DMUT="$mut" -s tb_full -o "$out/bench.vvp" physical/qwen_tile_glue_banks_1015/tb_full.sv rtl/qwen_sys/tile_glue_banks_20261015/qwen_glue_face_masters.sv rtl/qwen_sys/tile_glue_banks_20261015/ot_qwen_tile_full_face_composition.sv rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv rtl/lib/ot_rst_relay.sv
vvp "$out/bench.vvp"
