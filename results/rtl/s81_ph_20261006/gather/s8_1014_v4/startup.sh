#!/bin/bash
set -u
R=/srv/opentallas-scratch/claude/s81-gather-v4; S=$R/src; T=$S/rtl/dsrom_sys/s81_ph/test
SSA2=1 LOCAL_BANKS=1 DIE_CLOCKS=1 CONTROL_STRIP=1 SS=8 J=8 MODES="early" bash $T/run_gather_cl.sh $S $R/cl_early $T/real_order_trace.json "2" > $R/cl_early.out 2>&1
mkdir -p $R/startup; : > $R/startup/verdicts.log; n=0
for settings in "1 0" "1 2" "1 6" "4 0" "4 2" "4 6"; do
 read early phase <<< "$settings"
 $R/cluster/obj_base/sim +STIM=$R/cluster/real_L2.txt +EXPECT=0 +NEED=1 +EARLY_CMD=$early +RESET_PHASE=$phase +RESTART=1 > $R/startup/early${early}_phase${phase}.log 2>&1
 grep '^RESULT PASS' $R/startup/early${early}_phase${phase}.log >> $R/startup/verdicts.log && n=$((n+1))
 grep '^READY_SUMMARY' $R/startup/early${early}_phase${phase}.log >> $R/startup/verdicts.log
done
m=0
for early in 1 4; do
 $R/cl_early/obj_early/sim +STIM=$R/cluster/real_L2.txt +EXPECT=0 +NEED=1 +EARLY_CMD=$early +RESTART=1 > $R/startup/mut_early$early.log 2>&1
 grep -q '^RESULT PASS' $R/startup/mut_early$early.log || m=$((m+1))
 grep -h '^RESULT\|^READY_SUMMARY' $R/startup/mut_early$early.log >> $R/startup/verdicts.log
done
echo "STARTUP $n/6 PASS; EARLYSTART mutant FAIL $m/2" | tee -a $R/startup/verdicts.log
