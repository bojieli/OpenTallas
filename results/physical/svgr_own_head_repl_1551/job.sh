#!/bin/bash
set -euo pipefail
cd /
k=/srv/opentallas-scratch2/claude/codex-hbm-types-1551/svgr_head
docker run --name codex-svgrhead-1551 --cpus 2 --memory 4g --memory-swap 4g -v $k:/work openroad/orfs:asap7lock bash /work/run.sh > $k/bench.log 2>&1
