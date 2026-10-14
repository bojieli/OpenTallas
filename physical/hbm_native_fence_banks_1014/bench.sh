#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1"); mut=${2:-0}
mkdir -p "$out"
cd "$(dirname "$0")"
iverilog -g2012 -Ptb_fence_pinret.MUT="$mut" -Ptb_fence_pinret.SEED=7 -Ptb_fence_pinret.INPIN=1 -Ptb_fence_pinret.HOLDBUF=2 -o "$out/bench.vvp" -s tb_fence_pinret ./*.sv
vvp -n "$out/bench.vvp" > "$out/simulation.log" 2>&1 || { cat "$out/simulation.log"; exit 1; }
cat "$out/simulation.log"
grep -q '^FENCE_P PASS .*bad=0$' "$out/simulation.log"
