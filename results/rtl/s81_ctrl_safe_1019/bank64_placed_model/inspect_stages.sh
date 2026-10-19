#!/bin/bash
set -euo pipefail
model=/srv/opentallas-scratch/claude/codex-s81-ctrl-bank64/placed_model
docker run --rm -v "$model/work":/work:ro -v "$model":/model openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /model/inspect_stages.tcl' > "$model/inspect_stages.log" 2>&1
