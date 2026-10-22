#!/bin/bash
set -eu
OUT=${1:-out_axi};mkdir -p "$OUT"
# QE3-HROOT-PROMPT 10-21: 2nd arg prompt_safe6 = registered-read RX head (ot_hkv_prompt_mem_r)
SRC=${2:-prompt_safe};MEM=rtl/qwen_sys/host_cluster_20261017/prompt_safe/ot_hkv_prompt_mem.sv
[ "$SRC" != prompt_safe6 ]||MEM=rtl/qwen_sys/host_cluster_20261017/prompt_safe6/ot_hkv_prompt_mem_r.sv
sed 's/module qkd_host_axi_packet_ps/module qkd_host_axi_packet/' rtl/qwen_sys/host_cluster_20261017/$SRC/qkd_host_axi_packet_ps.sv > "$OUT/axi.sv"
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_qkd_host_axi_packet -Mdir "$OUT/obj" rtl/test/qwen_host/tb_qkd_host_axi_packet.sv "$OUT/axi.sv" $MEM physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v >"$OUT/build.log" 2>&1
"$OUT/obj/Vtb_qkd_host_axi_packet" >"$OUT/test.log" 2>&1
cat "$OUT/test.log"
grep -qi 'PASS' "$OUT/test.log"
