#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(mktemp -d /tmp/qwen-xepoch-bench.XXXXXX)
for bench in tb_qwen_xepoch_cache tb_qwen_xepoch_preload; do
  iverilog -g2012 -s "$bench" -o "$out/$bench" rtl/physical/ot_qwen_xepoch_cache.sv "rtl/test/qwen_kv_die/$bench.sv"
  vvp "$out/$bench"
done
iverilog -g2012 -s tb_qwen_xepoch_cache -Ptb_qwen_xepoch_cache.MUT=1 -o "$out/mutant" rtl/physical/ot_qwen_xepoch_cache.sv rtl/test/qwen_kv_die/tb_qwen_xepoch_cache.sv
if vvp "$out/mutant" >"$out/mutant.log" 2>&1; then echo 'FAIL stale-bank mutant escaped';exit 1;fi
rg -q 'epoch replay mismatch' "$out/mutant.log"
echo "PASS stale-bank mutant rejected; evidence $out"
