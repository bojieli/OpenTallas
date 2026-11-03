#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-hostcredit-top-2100
C=/srv/opentallas-scratch/claude/codex-kv-hostcredit-controller-2100
ot-run --mem 32 --threads 8 --hosts intel1 --no-spill --priority die --crit --disk 20 --dir "$R" -- bash "$R/resume_make.sh" > "$C/resume_build.client.log" 2>&1
printf 'RESUMED_BUILD_PASS_RUN_REQUESTED\n' > "$C/status"
ot-run --mem 16 --threads 1 --hosts intel1 --no-spill --priority die --crit --disk 20 --dir "$R" -- bash "$R/run_full.sh" > "$C/run.client.log" 2>&1
printf 'SCOPED_RUN_COMPLETE\n' > "$C/status"
