#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-recip-place-canary-prep-0810
python3 "$R/guard_canary.py" "$R" run
docker run --rm --name "codex-recip-place-final-read-$$" --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work:ro -v "$R/source":/src:ro -v "$R/final_read":/case -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash /case/inside_read.sh
