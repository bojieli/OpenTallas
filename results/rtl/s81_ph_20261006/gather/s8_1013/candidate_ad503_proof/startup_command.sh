#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/codex/s81-gather-leaf-v18/ad50382d0
mkdir -p "$R/startup"
: > "$R/startup/verdicts.log"
for settings in "1 0" "1 2" "1 6" "4 0" "4 2" "4 6";do
 read early phase <<< "$settings"
 "$R/cluster_ssa2/obj_base/sim" +STIM="$R/cluster_ssa2/real_L2.txt" +EXPECT=0 +NEED=1 +EARLY_CMD=$early +RESET_PHASE=$phase +RESTART=1 > "$R/startup/early${early}_phase${phase}.log" 2>&1
 grep '^RESULT PASS' "$R/startup/early${early}_phase${phase}.log" >> "$R/startup/verdicts.log"
 grep '^READY_SUMMARY' "$R/startup/early${early}_phase${phase}.log" >> "$R/startup/verdicts.log"
done
echo 'STARTUP_EQUIVALENCE PASS6 realL2 early-command/phase/drained-restart cases' | tee -a "$R/startup/verdicts.log"
