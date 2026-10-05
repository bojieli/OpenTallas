#!/usr/bin/env bash
set -uo pipefail
source "$HOME/.opentallas-env"
cd /srv/opentallas-scratch/codex/dsrom-wf-ctrl/wt-local-115e40246
export OT_ORFS_NUM_CORES=16
/srv/opentallas-scratch/admit.sh 12 -- python3 tools/dsrom_wf_close.py route --inst stg --local-control --run-dir /srv/opentallas-scratch/codex/dsrom-wf-ctrl/R13_local_stg
rc=$?
printf '%s\n' "$rc" > /srv/opentallas-scratch/codex/dsrom-wf-ctrl/R13_local_stg/exit_code
exit "$rc"
