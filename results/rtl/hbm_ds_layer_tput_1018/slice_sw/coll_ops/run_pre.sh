#!/usr/bin/env bash
# VEH-FMT-COLL2 pre-check: VEH-FMT-COLL's tb_coll_replay binary (Verilator 5.050, sw2 bundle gq + ring_ag + ring_b_stop
# + shares; sources.sha256 copied with it), every *.events.txt PASS, every mut/*.events.txt FAIL.
H=$(cd "$(dirname "$0")" && pwd); rc=0
for f in $H/*.events.txt; do n=$(basename $f .events.txt); $H/obj/Vtb_coll_replay +EV=$f > $H/$n.log 2>&1
 r=$(grep -m1 -E '^COLLRPL (PASS|FAIL)' $H/$n.log); echo "$n: $r"; echo "$r" | grep -q PASS || rc=1; done
for f in $H/mut/*.events.txt; do n=$(basename $f .events.txt); $H/obj/Vtb_coll_replay +EV=$f > $H/mut/$n.log 2>&1
 r=$(grep -m1 -E '^COLLRPL (PASS|FAIL)' $H/mut/$n.log); echo "MUT $n: $r"; grep -m2 MISMATCH $H/mut/$n.log; echo "$r" | grep -q FAIL || rc=1; done
exit $rc
