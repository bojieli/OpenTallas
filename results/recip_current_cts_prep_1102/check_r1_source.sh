#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-recip-cts-lifecycle-prep-1102r1
python3 "$R/guard_cts.py" "$R" pre
docker run --rm --name "codex-recip-cts-r1-source-$$" --memory=4g --memory-swap=4g --cpus=1 -v "$R/kit":/work:ro -v "$R/source":/src:ro -v "$R":/case -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 1 -exit /case/check_alias_closure.tcl'
bash "$R/run_cts_proposal.sh" dry
