#!/bin/bash
# gate5.sh <tag> <part a|b>: S81-LINKTO (0hn, 10-18) gate of the BUILT lane tiles on the switched array, cwd = staged repo
# root.  Same dense static calendar as gate4 (GAP 100, LAT 556, PER 1.345, backlog-aware deadlines).  Config = the tb
# defaults: dsfd_coll_lane_w/_e as built (tile-top CH_BOARD 700), ch_b 1 on every lane, ot_pdie_serdes on all 8 lanes of
# a die (0hn decision 2: UCIe cannot cross the switch).  No parameter what-if.
#   a: min (must PASS, 0 timeouts / replays), min_err (+ pad bit errors 1/7 cycles on all 32 SerDes lanes: PASS, identical
#      landings), chb0 (mutant: ch_b 0 = the UCIe basis CH_UCIE 100) and board400 (mutant: the pre-0hn tile, CH_BOARD 400,
#      ch_b 1) on the full calendar -- each must FAIL (ACK timeouts on the switched round trip -> late landings)
#   b: mutants on the reduced calendar: swap (lep), late (+40 cycles one lane), kp4d (DMUT 2 + pad errors) -- each must FAIL
set -u; T=$1; PART=$2; O=out_$T; mkdir -p $O
[ -f $O/g/NS ] || python3 tools/xdie_s81/gen_golden.py --out $O/g --gap 100 --lat S=556,N=556 --per S=1.345,N=1.345 > $O/gen_$PART.txt 2>&1
[ -f $O/gm/NS ] || python3 tools/xdie_s81/gen_golden.py --out $O/gm --reps 1 --only a_allgather,stage_hop --lat S=556,N=556 --per S=1.345,N=1.345 > $O/genm_$PART.txt 2>&1
r() { n=$1; g=$2; shift 2; ( J=6 bash tools/xdie_s81/run_xdie_s81.sh $O $n $O/$g ep "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt; grep -h XDIE_LINK $O/$n/run.log >> $O/$n.txt ) & }
if [ $PART = a ]; then
  r min g
  r min_err g -GERRP=7
  r chb0 g -GCHB=0
  r board400 g -GLOVR=1 -GCHB_OVR=400
else
  r swap gm -GMAXCYC=40000 +define+OT_S81SL_LEP_MUT_SWAP
  r late gm -GMAXCYC=40000 -GLATE_MUT=40
  r kp4d gm -GMAXCYC=40000 -GERRP=7 -GDMUT=2
fi
wait; touch $O/DONE_$PART
