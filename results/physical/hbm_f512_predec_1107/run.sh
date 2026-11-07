#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for m in 0 1; do /usr/bin/iverilog -g2012 -s tb -Ptb.MUT=$m -o test$m.vvp G/*.sv N/*.sv M/*.sv reset.sv sram.v tb.sv; /usr/bin/vvp test$m.vvp > result$m.log 2>&1; done
