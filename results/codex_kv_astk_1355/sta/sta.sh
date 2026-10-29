#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-astk-1355
K=$R/astk_base
B=$K/run/results/asap7/hc_kv3_astk__190_08x181_44/base
mkdir -p "$R/sta"
docker run --rm --name codex-astk1355-sta-$1 --cpus 4 --memory 12g --memory-swap 12g -e OT_DIAG_CORNER="$1" -v "$K":/work:ro -v "$B":/base:ro -v "$R/sta":/out -w /out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 4 -exit /out/sta.tcl' > "$R/sta/$1.log" 2>&1
