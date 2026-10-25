#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
yosys -Q -p 'read_verilog -formal -sv transport.sv miter.sv; prep -top miter -flatten; async2sync; opt; sat -seq 14 -set-init-zero -set-assumes -prove-asserts -verify' > proof.log 2>&1
set +e
yosys -Q -p 'read_verilog -formal -sv transport.sv miter.sv; chparam -set MUT 1 miter; prep -top miter -flatten; async2sync; opt; sat -seq 14 -set-init-zero -set-assumes -prove-asserts -verify' > mutant.log 2>&1
r=$?
set -e
if [ "$r" -eq 0 ]; then echo MUTANT_ESCAPED; exit 1; fi
grep -q 'proof did fail' mutant.log
echo F2B_FORMAL_PASS_MUTANT_CAUGHT
