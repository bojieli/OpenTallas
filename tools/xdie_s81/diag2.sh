#!/bin/bash
set -u; O=out_diag2; mkdir -p $O
[ -f $O/g/NS ] || python3 tools/xdie_s81/gen_golden.py --out $O/g --reps 1 --only argmax_merge,a_allgather > $O/gen.txt 2>&1
J=8 bash tools/xdie_s81/run_xdie_s81.sh $O asb $O/g ep -GCHB=0 > $O/asb.txt 2>&1; echo "EXIT $?" >> $O/asb.txt; grep -E "Maximum resident|Elapsed" $O/asb/time_build.log $O/asb/time_run.log >> $O/asb.txt
touch $O/DONE
