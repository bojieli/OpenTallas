#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(mktemp -d /tmp/qwen-xline-bench.XXXXXX)
iverilog -g2012 -s tb_qwen_xline_roots -o "$out/roots" rtl/physical/ot_qwen_xline_delivery.sv rtl/test/qwen_kv_die/tb_qwen_xline_roots.sv
vvp "$out/roots"
iverilog -g2012 -s tb_qwen_xline_delivery -o "$out/capture" rtl/physical/ot_qwen_xline_delivery.sv rtl/physical/ot_qwen_die_station.sv rtl/test/qwen_kv_die/tb_qwen_xline_delivery.sv
vvp "$out/capture"
iverilog -g2012 -s tb_qwen_xline_delivery -Ptb_qwen_xline_delivery.MUT=1 -o "$out/mutant" rtl/physical/ot_qwen_xline_delivery.sv rtl/physical/ot_qwen_die_station.sv rtl/test/qwen_kv_die/tb_qwen_xline_delivery.sv
if vvp "$out/mutant" >"$out/mutant.log" 2>&1; then
    echo "FAIL mutant escaped"; exit 1
fi
rg -q 'wrong distinct line' "$out/mutant.log"
echo "PASS broadcast-line mutant rejected; evidence $out"
