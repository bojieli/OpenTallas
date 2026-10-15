#!/bin/bash
set -euo pipefail
iverilog -g2012 -s tb -o proof.vvp ctfn_original.sv ot_s81_hc_ctfn_columns_candidate.sv tb_ctfn_columns.sv
vvp proof.vvp | tee positive.log
for m in 1 2 3 4 5 6 7 8; do
 if vvp proof.vvp +MUTANT=$m > mutant$m.log 2>&1; then echo "UNEXPECTED_MUTANT_PASS $m";exit 1;fi
 if ! rg -q "OBSERVED_MISMATCH mutant=$m cycle=99" mutant$m.log; then cat mutant$m.log;exit 1;fi
 echo "MISSING_CLOCK_MUTANT_FAIL_OBSERVED $m"
done
