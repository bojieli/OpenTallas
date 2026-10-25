#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
for m in 0 1;do iverilog -g2012 -DMUT=$m -s tb -o sim$m dut.sv tb.sv;vvp sim$m > run_m$m.log;done
grep -q '^PASS$' run_m0.log
grep -q '^FAIL$' run_m1.log
cat run_m0.log run_m1.log
