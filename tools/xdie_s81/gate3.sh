#!/bin/bash
# gate3.sh <tag>: dense calendar (GAP 100) + compiled deadlines (LAT 556, PER 1.345) on WHAT-IF link-layer sizings for
# the switched crossing (cwd = staged repo root).  The p4l RTL with ch_b 0 / 1 FAILS this calendar (out_g1 / out_g2).
#   min       ot_s81ph_coll_lane CH_BOARD 700 (ACK timeout basis > switched RTT), CREDITS 512 / SEQW 10 / SRAM as built
#   full      CH_BOARD 700, CREDITS 1024, SEQW 11 (flop arrays: SRAM macros are <= 512 deep)
#   min_err   min + pad bit errors on every SerDes lane (1 bit / 7 cycles): KP4 corrects, must PASS exact on time
#   min_kp4d  min_err + KP4 decoder mutant DMUT 2 (mutant calendar): must FAIL
set -u; T=$1; O=out_$T; mkdir -p $O
python3 tools/xdie_s81/gen_golden.py --out $O/g --gap 100 --lat S=556,N=556 --per S=1.345,N=1.345 > $O/gen.txt 2>&1 || exit 2
python3 tools/xdie_s81/gen_golden.py --out $O/gm --reps 1 --only a_allgather,stage_hop --lat S=556,N=556 --per S=1.345,N=1.345 > $O/genm.txt 2>&1
MIN="-GCHB=1 -GLOVR=1 -GCHB_OVR=700 -GCRED_OVR=512 -GSEQW_OVR=10 -GLSRAM=1"
r() { n=$1; g=$2; shift 2; ( J=6 bash tools/xdie_s81/run_xdie_s81.sh $O $n $O/$g ep "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt; grep -h XDIE_LINK $O/$n/run.log >> $O/$n.txt ) & }
r min g $MIN
r full g -GCHB=1 -GLOVR=1 -GCHB_OVR=700 -GCRED_OVR=1024 -GSEQW_OVR=11 -GLSRAM=0
r min_err g $MIN -GERRP=7
r min_kp4d gm $MIN -GERRP=7 -GDMUT=2 -GMAXCYC=40000
wait; touch $O/DONE
