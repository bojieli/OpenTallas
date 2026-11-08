#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/runtime"
iverilog -g2012 -s tb -o native.vvp common.sv off.sv on.sv tb.sv
for seed in 1 1592639215; do
  timeout 240 vvp native.vvp +SEED="$seed" > "seed${seed}.log" 2>&1
done
iverilog -g2012 -s tb -o mutant.vvp common.sv off.sv on_mut.sv tb.sv
if timeout 240 vvp mutant.vvp +SEED=1 > mutant.log 2>&1; then
  echo "FAIL: neighbor-mask mutant survived" >&2
  exit 8
fi
grep -q 'WQDIAG_EDGE' mutant.log
