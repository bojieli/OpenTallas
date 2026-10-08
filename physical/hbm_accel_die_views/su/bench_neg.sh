#!/bin/bash
# negative control of a quarter envelope (bench.sh's step 3 alone): lane 1's first per-lane result bits one slot off
# must FAIL the generator reference.   bench_neg.sh <quarter> <outdir>  (run in src)
set -u; q=$1; O=$2; m=hfd_$q; mkdir -p $O
python3 tools/hbm_die_views.py ${VARIANT:+--variant $VARIANT} ports --master $m --out $O/ports > /dev/null
python3 tools/hbm_hub_quarter_gen.py --quarter $q --ports $O/ports/$m/ports.json --out $O/gen ${TWO_SIDED:+--two-sided} > $O/plan.log
cd $O/gen && iverilog -g2012 -o simn tb_$m.sv ${m}_neg.sv *_simstub.sv && vvp -n simn > neg.log; rc=$?
grep OT_RESULT neg.log; grep -q "FAIL" neg.log && echo QUARTER_NEG_FAIL; exit $rc
