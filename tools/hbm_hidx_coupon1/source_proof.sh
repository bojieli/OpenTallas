#!/bin/bash
set -euo pipefail
mkdir -p out
T=tools/hbm_hidx_coupon1
iverilog -g2012 -s tb -o out/sim "$T/coupon.sv" "$T/tb.sv"
vvp out/sim >out/pass.log
for m in 1 2 3 4 5; do
 iverilog -g2012 -DMUT=$m -s tb -o out/mut$m "$T/coupon.sv" "$T/tb.sv"
 if vvp out/mut$m >out/mut$m.log 2>&1; then echo "unexpected mutant$m PASS";exit 1;fi
 grep -Eq 'COMPACT_ORDER_PREFIX_COPY_FAIL|PAIR_COUNT_COPY_FAIL' out/mut$m.log
done
