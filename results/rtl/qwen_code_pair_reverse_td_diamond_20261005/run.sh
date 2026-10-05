#!/bin/bash
set -uo pipefail
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
export OMP_NUM_THREADS=16 OT_ORFS_NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
job=/srv/opentallas-scratch/codex/kant-code-pair-reverse-td-diamond-20261005-r2
/srv/opentallas-scratch/admit.sh 64 -- python3 "$job/source/qwen_code_pair_reverse_resume.py" --retained-work /srv/opentallas-scratch/codex/kant-code-pair-banklocal-reversebanks-20261005-r1/route --source-dir /srv/opentallas/repos/pauli-code-banklocal-route-337969217 --work "$job/route" --claude-td-diamond > "$job/supervisor.log" 2>&1
rc=$?
echo "$rc" > "$job/supervisor.exit"
exit "$rc"
