#!/bin/bash
set -u
cd /srv/opentallas-scratch/codex/h7-additive0922
rc=0
iverilog -V 2>/dev/null | head -1
for m in none 0 1 2 3 4 5;do
 bash tools/hbm_die_v15/bench_pc_ctrl_faults.sh out$m "$m" > bench$m.log 2>&1
 r=$?
 echo "ROW fault_mutant=$m rc=$r";tail -4 bench$m.log
 if [ "$m" = none ];then [ "$r" = 0 ] && grep -q PC_CTRL_FAULTS_GATE_PASS bench$m.log || rc=1
 else [ "$r" = 1 ] && grep -q '^FATAL:.*FAULT_CLASS mismatch' bench$m.log || rc=1;fi
done
exit $rc
