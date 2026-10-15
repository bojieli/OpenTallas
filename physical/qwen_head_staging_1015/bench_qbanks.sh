#!/usr/bin/env bash
set -euo pipefail
out=$1
mutant=${2:-0}
mkdir -p "$out"
iverilog -g2012 -s tb_qpacket_banks -Ptb_qpacket_banks.MUT="$mutant" -o "$out/bench.vvp" rtl/test/qwen_head_staging/tb_qpacket_banks.sv rtl/qwen_sys/head_staging_20261015/ot_qkh_qpacket_banks.sv rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv rtl/lib/ot_rst_relay.sv
vvp "$out/bench.vvp" | tee "$out/result.log"
if grep -q '^FAIL ' "$out/result.log"; then exit 1; fi
