#!/bin/bash
set -euo pipefail
O=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name codex-hbm-$(basename "$O") --memory=8g --memory-swap=8g --cpus=8 -v "$O:/o" openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /o/feed_route.tcl > /o/route.log 2>&1; for c in TT FF; do CORNER=$c openroad -no_init -threads 2 -exit /o/feed_sta.tcl > /o/sta_$c.log 2>&1; done'
