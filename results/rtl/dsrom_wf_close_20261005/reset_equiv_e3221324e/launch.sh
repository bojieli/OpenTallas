#!/usr/bin/env bash
O=/srv/opentallas-scratch/codex/dsrom-wf-ctrl/reset_equiv_e3221324e
bash "$O/run.sh"
rc=$?
echo "$rc" > "$O/exit_code"
exit "$rc"
