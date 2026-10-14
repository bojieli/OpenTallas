#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1"); mut=${2:-0}
mkdir -p "$out"
cd "$(dirname "$0")/../.."
iverilog -g2012 -Ptb_fence_pinret.MUT="$mut" -Ptb_fence_pinret.SEED=7 -Ptb_fence_pinret.INPIN=1 -Ptb_fence_pinret.HOLDBUF=2 -o "$out/bench.vvp" -s tb_fence_pinret physical/hbm_native_fence_clocked_1014/*.sv physical/hbm_native_fence_banks_1014/ot_hbm_native_fence_fifo_bank.sv physical/hbm_native_fence_banks_1014/ot_hbm_native_fence_bank_family.sv
vvp -n "$out/bench.vvp" > "$out/simulation.log" 2>&1 || { cat "$out/simulation.log"; exit 1; }
cat "$out/simulation.log"
grep -q '^FENCE_P PASS .*bad=0$' "$out/simulation.log"
