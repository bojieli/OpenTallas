#!/bin/bash
set -uo pipefail
job=/srv/opentallas-scratch2/jobs/pauli-code-banklocal-constant-ties-r3
while [ ! -f "$job/supervisor.exit" ]; do sleep 30; done
rc=$(cat "$job/supervisor.exit")
if [ "$rc" != 0 ]; then
 echo "Route terminal $rc; retained tied checkpoint, no routed SS/FF claim."
 echo "$rc" > "$job/finish.exit"
 exit "$rc"
fi
/srv/opentallas-scratch/admit.sh 64 -- python3 /srv/opentallas-scratch/codex/pauli-code-banklocal-td-diamond-r2/helpers/qwen_code_pair_banklocal_corner.py \
 --orfs-dir "$job/orfs" \
 --source-dir /srv/opentallas-scratch/codex/pauli-code-banklocal-td-diamond-r2/source \
 --output "$job/orfs/corner_sta.json"
rc=$?
echo "$rc" > "$job/finish.exit"
exit "$rc"
