#!/bin/bash
# gate4.sh <tag> <part a|b>: FINAL gate on the dense static calendar (GAP 100, LAT 556, PER 1.345, backlog-aware
# deadlines), cwd = staged repo root.
#   a: min (CH_BOARD 700 what-if, else as built) PASS?, min_err (+ pad errors, KP4 corrects) PASS?, asbuilt (ch_b 0) and
#      board (ch_b 1) = the built p4l lane tiles (expected FAIL: ACK timeouts on the switched RTT)
#   b: mutants on min: swap (lep), late (+40 cycles one lane), kp4d (DMUT 2 + pad errors) -- each must FAIL
set -u; T=$1; PART=$2; O=out_$T; mkdir -p $O
[ -f $O/g/NS ] || python3 tools/xdie_s81/gen_golden.py --out $O/g --gap 100 --lat S=556,N=556 --per S=1.345,N=1.345 > $O/gen_$PART.txt 2>&1
[ -f $O/gm/NS ] || python3 tools/xdie_s81/gen_golden.py --out $O/gm --reps 1 --only a_allgather,stage_hop --lat S=556,N=556 --per S=1.345,N=1.345 > $O/genm_$PART.txt 2>&1
MIN="-GCHB=1 -GLOVR=1 -GCHB_OVR=700 -GCRED_OVR=512 -GSEQW_OVR=10 -GLSRAM=1"
r() { n=$1; g=$2; shift 2; ( J=6 bash tools/xdie_s81/run_xdie_s81.sh $O $n $O/$g ep "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt; grep -h XDIE_LINK $O/$n/run.log >> $O/$n.txt ) & }
if [ $PART = a ]; then
  r min g $MIN
  r min_err g $MIN -GERRP=7
  r asbuilt g -GCHB=0
  r board g -GCHB=1
else
  r swap gm $MIN -GMAXCYC=40000 +define+OT_S81SL_LEP_MUT_SWAP
  r late gm $MIN -GMAXCYC=40000 -GLATE_MUT=40
  r kp4d gm $MIN -GMAXCYC=40000 -GERRP=7 -GDMUT=2
fi
wait; touch $O/DONE_$PART
