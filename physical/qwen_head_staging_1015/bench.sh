#!/usr/bin/env bash
set -euo pipefail
out=$1
width=${2:-519}
mutant=${3:-0}
master=${4:-}
args=()
if [[ -n "$master" ]]; then args+=("-DQKH_PACKET_DUT=$master"); fi
mkdir -p "$out"
iverilog -g2012 "${args[@]}" -s tb_packet_stage -Ptb_packet_stage.W="$width" -Ptb_packet_stage.MUT="$mutant" -o "$out/bench.vvp" rtl/test/qwen_head_staging/tb_packet_stage.sv rtl/qwen_sys/head_staging_20261015/ot_qkh_packet_stage.sv rtl/lib/ot_rst_relay.sv rtl/qwen_sys/head_staging_20261015/qkh_packet_masters.sv
vvp "$out/bench.vvp" | tee "$out/result.log"
if grep -q '^FAIL ' "$out/result.log"; then exit 1; fi
