#!/bin/bash
R=/srv/opentallas-scratch/claude/s81-shlk12
S=$R/scripts/run_lockstep.sh
export SEGS=${SEGS:-1500}
bash $S $R/ls_base "1 2 3 4 5 6 7 8 9 10 11 12" > $R/ls_base.out 2>&1 &
for m in BYP GOD WIN KIND FQS CQR; do bash $S $R/ls_mut_$m "1 2 3" -DOT_N32_MUT_$m > $R/ls_mut_$m.out 2>&1 & done
wait
for d in ls_base ls_mut_BYP ls_mut_GOD ls_mut_WIN ls_mut_KIND ls_mut_FQS ls_mut_CQR; do echo "== $d"; grep -h -i "LOCKSTEP\|fatal\|diverged" $R/$d/run_*.log | cut -c1-200; done
