#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/runtime"
iverilog -g2012 -s tb -o native.vvp common.sv off.sv on.sv tb.sv
for seed in 1 1592639215; do
  timeout 240 vvp native.vvp +SEED="$seed" > "seed${seed}.log" 2>&1
done
