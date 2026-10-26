#!/bin/bash
# pilot1.sh <tag> <name> [verilator args]: one configuration of the calibration pilot (cwd = staged repo root)
set -u; T=$1; N=$2; shift 2; O=out_$T; mkdir -p $O
[ -f $O/g_cal/NS ] || python3 tools/xdie_s81/gen_golden.py --out $O/g_cal > $O/gen.txt 2>&1 || { echo GEN_FAILED; exit 2; }
J=8 bash tools/xdie_s81/run_xdie_s81.sh $O $N $O/g_cal ep "$@" > $O/$N.txt 2>&1; echo "EXIT $?" >> $O/$N.txt
grep -E "Maximum resident|Elapsed" $O/$N/time_build.log $O/$N/time_run.log 2>/dev/null >> $O/$N.txt; cat $O/$N.txt
