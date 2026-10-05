#!/bin/bash
set -uo pipefail
job=/srv/opentallas-scratch2/jobs/pauli-code-banklocal-constant-ties-r3
mkdir -p "$job/tmp"
export TMPDIR="$job/tmp" OMP_NUM_THREADS=16 OT_FLOW_TIMEOUT_SECONDS=unlimited
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
ulimit -m unlimited
/srv/opentallas-scratch/admit.sh 64 -- python3 /srv/opentallas-scratch2/jobs/pauli-codepair-tie-helper-20261005/qwen_code_pair_tie_resume.py \
 --retained-work /srv/opentallas-scratch/codex/pauli-code-banklocal-td-diamond-r2/orfs \
 --source-dir /srv/opentallas-scratch/codex/pauli-code-banklocal-td-diamond-r2/source \
 --work "$job/orfs"
rc=$?
echo "$rc" > "$job/supervisor.exit"
exit "$rc"
