#!/bin/bash
set -u
T=${1:?}
R=/srv/opentallas-scratch/claude/codex-qdie-2000/$T
while :; do
  test "$(ssh ot-gold1 "test -s $R/chain/PREPARED_WAIT_GRT && echo ready")" = ready && break
  sleep 30
done
exec /home/ubuntu/bin/ot-run --mem 200 --threads 8 --disk 100 --priority die --dir "$R" -- bash guarded_resume200.sh
