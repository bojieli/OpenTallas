#!/bin/bash
set -euo pipefail
cd /work
for m in 0 1 2; do
 f=slice.sv; [ "$m" = 0 ] || f=slice_mut$m.sv
 iverilog -g2012 -s tb -Ptb.MUT=$m -o sim$m.vvp "$f" tb.sv
 vvp -n sim$m.vvp > result$m.log 2>&1
 cat result$m.log
done
