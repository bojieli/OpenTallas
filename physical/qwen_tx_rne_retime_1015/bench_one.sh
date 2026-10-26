#!/usr/bin/env bash
set -euo pipefail
out=${1:?out};mut=${2:-0};mkdir -p "$out"
iverilog -g2012 -s tb_tx_rne -Ptb_tx_rne.MUT="$mut" -o "$out/sim.vvp" physical/qwen_tx_rne_retime_1015/tb_tx_rne.sv rtl/qwen_sys/tx_rne_retime_20261015/qwen_tx_rne.sv rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv rtl/lib/ot_rst_relay.sv > "$out/compile.log" 2>&1
rc=0;vvp "$out/sim.vvp" > "$out/result.log" 2>&1||rc=$?
cat "$out/result.log"
exit "$rc"
