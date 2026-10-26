#!/bin/bash
# HBM-B-RTL2: run the split lockstep cases on the binaries chain3.sh builds (obj_s0 / obj_s4 / obj_s1); waits for each binary.
set -u
R=$(cd "$(dirname "$0")" && pwd); O=$R/out5; mkdir -p $O
V(){ echo "$(date -Is) $*" >> $O/verdict.txt; }
run(){ # bin case tag
  local d=$O/$3; rm -rf $d; cp -r $R/cases/$2 $d
  ( cd $d && /usr/bin/time -v $R/obj_$1/V$1 $(cat plus.txt) > run.log 2>&1; echo RUN_RC=$? >> run.log )
  grep -h "HC_ENG_DONE\|HC_ENG PASS\|HC_ENG FAIL\|FAULT\|MISMATCH\|watchdog\|RUN_RC\|Elapsed" $d/run.log | head -8 | sed "s|^|  $3: |" >> $O/verdict.txt
}
waitbin(){ while [ ! -x $R/obj_$1/V$1 ]; do pgrep -f "chain3.sh" >/dev/null || return 1; sleep 30; done; }
V "runs start host=$(hostname)"
run s0 s_probe s_probe & run s0 s_p1 s_p1 & run s0 s_p2 s_p2 & run s0 s_p8 s_p8 &
run s0 s_g22 s_g22 & run s0 s_neg164 s_neg164 & run s0 s_mutdata s_mutdata &
( waitbin s4 && run s4 s_p1 s_mut4_p1 || V "no s4 binary" ) &
( waitbin s1 && run s1 s_p1 s_mut1_p1 || V "no s1 binary" ) &
wait
grep -m3 "PROBE raw" $O/s_probe/run.log | sed 's/^/  probe: /' >> $O/verdict.txt
V "runs done"
