#!/bin/bash
set -euo pipefail
O=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name codex-hbm-nw-calibrate-$(basename "$O") --memory=2g --memory-swap=2g --cpus=1 -v "$O:/o" openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for corner in TT FF; do CORNER=$corner openroad -no_init -threads 1 -exit /o/recalibrate_nw.tcl > /o/calibrate_$corner.log 2>&1; done'
