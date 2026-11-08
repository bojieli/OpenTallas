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
iverilog -g2012 -s tb -Ptb.RELOAD=151 -o misaligned.vvp common.sv off.sv on.sv tb.sv
if timeout 60 vvp misaligned.vvp +SEED=1 > misaligned.log 2>&1; then
  echo "FAIL: illegal 833 row-phase calendar survived" >&2
  exit 9
fi
grep -q 'WQDIAG_REFRESH_PHASE' misaligned.log
