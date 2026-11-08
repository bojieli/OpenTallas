#!/bin/bash
set -euo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
R=/srv/opentallas-scratch2/claude/codex-s81-rck-0222/work
E=$R/results/s81_rck_11_reform_1108/cland_local
for m in base old_on old_align slot;do bash "$E/run_one.sh" "$R" "$E" "$m";done
