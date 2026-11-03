#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-recip-place-canary-prep-0810
MODE=${1:-dry}
case "$MODE" in dry|run) ;; *) exit 64 ;; esac
python3 "$R/guard_canary.py" "$R" pre
# No OT_PG_STRICT environment forwarding/override: preserve actual121 manual UNSET.
docker run --rm --name "codex-recip-private-pg-${MODE}-$$" --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work -v "$R/source":/src:ro -v "$R":/case -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash /case/inside_canary.sh "$MODE"
python3 "$R/guard_canary.py" "$R" "$MODE"
