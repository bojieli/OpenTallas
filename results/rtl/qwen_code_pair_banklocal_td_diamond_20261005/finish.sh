#!/bin/bash
set -uo pipefail
job=/srv/opentallas-scratch/codex/pauli-code-banklocal-td-diamond-r2
while [ ! -f "$job/supervisor.exit" ]; do sleep 30; done
rc=$(cat "$job/supervisor.exit")
if [ "$rc" != 0 ]; then
  echo "Route terminal $rc; no final routed SS/FF checkpoint."
  echo "$rc" > "$job/finish.exit"
  exit "$rc"
fi
/srv/opentallas-scratch/admit.sh 64 -- python3 "$job/helpers/qwen_code_pair_banklocal_corner.py" \
  --orfs-dir "$job/orfs" --source-dir "$job/source" --output "$job/orfs/corner_sta.json"
rc=$?
echo "$rc" > "$job/finish.exit"
exit "$rc"
