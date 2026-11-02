#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch2/claude/codex-s81-l2-B10-sta2
K=/srv/opentallas-scratch2/claude/codex-s81-l2-B10-portable/kit
printf "START %s\n" "$(date -Is)" >> $R/status
SIGNOFF_DOCKER=$R/docker4.sh python3 -I $R/flow/tools/die_plan/signoff.py run --run-dir $K/run --kit $K --corners tt,ff --out $R/signoff --image openroad/orfs:asap7lock > $R/signoff.log 2>&1
s=$?; printf "SIGNOFF_RC %s %s\n" "$s" "$(date -Is)" >> $R/status
exit "$s"
