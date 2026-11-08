#!/bin/bash
set -euo pipefail
cd /
k=/srv/opentallas-scratch2/claude/codex-hbm-types-1551/svgr_head
bash $k/run_host.sh > $k/bench2.log 2>&1
