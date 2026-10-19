#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/codex-pvm-mirror-census16
mkdir -p "$R/work"
cp "$R/config.mk" "$R/work/config.mk"
docker run --rm -e LEC_CHECK=0 -v "$R/src:/src:ro" -v "$R/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > "$R/synth.log" 2>&1
