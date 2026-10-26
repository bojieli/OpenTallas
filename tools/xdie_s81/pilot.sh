#!/bin/bash
# pilot.sh <tag> : TOKEN-XDIE-S81 calibration pilot (cwd = staged repo root). Three lane configurations, no deadlines.
#   asbuilt  ch_b 0 (the p4l plan strap: UCIe timeout basis), stock lane tiles
#   board    ch_b 1 (board timeout basis CH_BOARD 400), stock lane tiles
#   sized    WHAT-IF lane params for a switched crossing: CH_BOARD 700, CREDITS 1024, SEQW 11 (flop arrays)
set -u; T=${1:-p1}; O=out_$T; mkdir -p $O
python3 tools/xdie_s81/gen_golden.py --out $O/g_cal > $O/gen.txt 2>&1 || { echo GEN_FAILED; cat $O/gen.txt; exit 2; }
run() { n=$1; shift; ( J=6 bash tools/xdie_s81/run_xdie_s81.sh $O $n $O/g_cal ep "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt ) & }
run asbuilt -GCHB=0
run board   -GCHB=1
run sized   -GCHB=1 -GLOVR=1 -GCHB_OVR=700 -GCRED_OVR=1024 -GSEQW_OVR=11 -GLSRAM=0
wait; touch $O/DONE
