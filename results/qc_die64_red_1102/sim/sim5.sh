#!/bin/bash
cd /home/ubuntu/scratch-root/claude/die-qc-63-red/sim5; ulimit -v 32000000
./comp.sh o5 "" & ./comp.sh mrdv -DOT_RED_MUT_RDV & ./comp.sh mbusy -DOT_RED_MUT_BUSY & ./comp.sh ml4 -DLEXP=4 & wait
for s in 21 22 23 24 25 26; do timeout 5h vvp -n o5.vvp +cycles=12000 +seed=$s > o5_s$s.log 2>&1 & done
for m in mrdv mbusy ml4; do timeout 3h vvp -n $m.vvp +cycles=3000 +seed=7 > $m.log 2>&1 & done
wait; echo ALLDONE > sim5.done
