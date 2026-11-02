#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-recip-cts-lifecycle-prep-1102r0
MODE=${1:-dry}
case "$MODE" in dry|run) ;; *) exit 64 ;; esac
python3 "$R/guard_cts.py" "$R" pre
# Original manual context is UNSET; no strict value or unsupported alias override.
docker run --rm --name "codex-recip-private-cts-${MODE}-$$" --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work -v "$R/source":/src:ro -v "$R":/case -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash /case/inside_cts_proposal.sh "$MODE"
python3 "$R/guard_cts.py" "$R" "$MODE"
