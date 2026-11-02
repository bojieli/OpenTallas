#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102
D=$R/grt_only
# Do not run on a partial global-route checkpoint.
grep -q 'DPL_DATA_GRT_COMPLETE_REOPENED_PG_PASS_NOT_SIGNED' "$D/RESULT"
docker run --rm --name codex-pc-fresh-grt-geometry-read --memory=8g --memory-swap=8g --cpus=1 -v "$D":/work:ro -v "$R/geometry_read":/case sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec openroad -exit -no_init -threads 1 -python /case/read_geometry.py'
