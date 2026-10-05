#!/usr/bin/env bash
set -uo pipefail
cd /srv/opentallas-scratch/codex/ampere-qwen-rom-die-item7-capture-binary-20261004/src || exit 4
bash tools/qwen_slab_capture_gate.sh /srv/opentallas-scratch/codex/ampere-qwen-rom-die-item7-capture-binary-20261004/gate
rc=$?
echo "$rc" > /srv/opentallas-scratch/codex/ampere-qwen-rom-die-item7-capture-binary-20261004/job.exit
exit "$rc"
