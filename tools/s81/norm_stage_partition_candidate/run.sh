#!/bin/bash
set -euo pipefail
iverilog -g2012 -s tb -o proof.vvp ctfn_original.sv ot_s81_hc_ctfn_columns_candidate.sv tb_ctfn_columns.sv
vvp proof.vvp | tee positive.log
python3 -c 'import pathlib,re;assert re.search(r"^LOCKSTEP_PASS cycles=2048 checks=5970192 mutant=0$",pathlib.Path("positive.log").read_text(),re.M)'
for m in 1 2 3 4 5 6 7 8; do
 if vvp proof.vvp +MUTANT=$m > mutant$m.log 2>&1; then echo "UNEXPECTED_MUTANT_PASS $m";exit 1;fi
 python3 -c 'import pathlib,re,sys;m=sys.argv[1];assert re.search(r"^OBSERVED_MISMATCH mutant="+m+r" cycle=99 ",pathlib.Path("mutant"+m+".log").read_text(),re.M)' "$m"
 echo "MISSING_CLOCK_MUTANT_FAIL_OBSERVED $m"
done
