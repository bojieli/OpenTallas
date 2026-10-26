#!/usr/bin/env bash
H=$(cd "$(dirname "$0")" && pwd); rc=0
for f in $H/mut/*.events.txt; do n=$(basename $f .events.txt); $H/obj/Vtb_coll_replay +EV=$f > $H/mut/$n.log 2>&1
 r=$(grep -m1 -E '^COLLRPL (PASS|FAIL)' $H/mut/$n.log); echo "$n: $r"; grep -m2 MISMATCH $H/mut/$n.log; echo "$r" | grep -q FAIL || rc=1; done; exit $rc
