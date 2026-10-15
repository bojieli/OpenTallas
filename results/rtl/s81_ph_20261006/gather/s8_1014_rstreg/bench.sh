#!/bin/bash
set -u
R=/srv/opentallas-scratch/claude/s81-gather-1014/3a30f458b; S=$R/src; T=$S/rtl/dsrom_sys/s81_ph/test
SSA2=1 LOCAL_BANKS=1 DIE_CLOCKS=1 CONTROL_STRIP=1 SS=8 J=4 MODES="base lane chain nofwd xgo ovf rstreg early" bash $T/run_gather_cl.sh $S $R/cluster $T/real_order_trace.json "2 20" > $R/cluster.out 2>&1; c=$?
r=0  # root gate already PASS 274 (root.out)
mkdir -p $R/startup; : > $R/startup/verdicts.log; n=0
for settings in "1 0" "1 2" "1 6" "4 0" "4 2" "4 6"; do
 read early phase <<< "$settings"
 $R/cluster/obj_base/sim +STIM=$R/cluster/real_L2.txt +EXPECT=0 +NEED=1 +EARLY_CMD=$early +RESET_PHASE=$phase +RESTART=1 > $R/startup/early${early}_phase${phase}.log 2>&1
 grep '^RESULT PASS' $R/startup/early${early}_phase${phase}.log >> $R/startup/verdicts.log && n=$((n+1))
 grep '^READY_SUMMARY' $R/startup/early${early}_phase${phase}.log >> $R/startup/verdicts.log
done
echo "STARTUP $n/6 PASS" | tee -a $R/startup/verdicts.log
tail -3 $R/cluster.out; grep GATE $R/root.out | tail -1
echo "BENCH_DONE cluster=$c root=$r startup=$n"
