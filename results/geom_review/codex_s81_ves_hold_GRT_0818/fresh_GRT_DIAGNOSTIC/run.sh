#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-ves-gate-fresh-0830/kit
test -f "$K/saved_GRT_PG.json"
docker run --rm --memory=4g --memory-swap=4g --cpus=2 -e OT_PG_STRICT=1 -v "$K":/work -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -eo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/readout.py' > "$K/readout.log" 2>&1
