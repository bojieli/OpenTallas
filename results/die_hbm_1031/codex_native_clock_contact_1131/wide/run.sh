#!/bin/bash
set -euo pipefail
O=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name codex-hbm-$(basename "$O") --memory=4g --memory-swap=4g --cpus=4 -v "$O:/o" openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /o/native_tail_route.tcl > /o/route.log 2>&1; for corner in TT FF; do CORNER=$corner openroad -no_init -threads 1 -exit /o/native_tail_sta.tcl > /o/sta_$corner.log 2>&1; done'
