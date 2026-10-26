#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-n59-1026
bash "$R/trial_flat/gen/run_kit.sh" "$R/trial_flat/gen/native59" floorplan 32 16
