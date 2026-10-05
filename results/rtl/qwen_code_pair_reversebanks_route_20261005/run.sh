#!/bin/bash
set -uo pipefail
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
export OMP_NUM_THREADS=16 OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
job=/srv/opentallas-scratch/codex/kant-code-pair-banklocal-reversebanks-20261005-r1
/srv/opentallas-scratch/admit.sh 64 -- python3 "$job/route_helper.py" --source-dir /srv/opentallas/repos/pauli-code-banklocal-route-337969217 --mapped-dir "$job/reuse/mapped" --slot-dir "$job/inputs/code_pair_reversebanks" --work "$job/route" --nickname kant_code_banklocal_reverse_ac019_r1 --image sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 > "$job/supervisor.log" 2>&1
rc=$?
echo "$rc" > "$job/supervisor.exit"
exit "$rc"
