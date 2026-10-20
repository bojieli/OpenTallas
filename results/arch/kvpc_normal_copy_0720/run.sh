#!/bin/bash
set -euo pipefail
for mut in 0 1 2 3; do
 docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock yosys -Q -T -p "read_verilog -sv coupon.v; chparam -set MUT $mut coupon; hierarchy -top coupon; proc; flatten; opt_clean; sat -seq 16 -set rst_n 1 -set-at 1 rst_n 0 -prove ok 1 -verify -show-inputs -show-outputs" > "mut${mut}.log" 2>&1 && rc=0 || rc=$?
 echo "MUT=$mut RC=$rc"
 if [ "$mut" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; fi
 done
