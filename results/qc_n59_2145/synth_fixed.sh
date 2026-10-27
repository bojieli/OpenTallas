#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-n59-2145-fixed/kit
sudo docker run --rm -v "$K:/work" openroad/orfs:latest bash -lc "cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run NUM_CORES=16 synth"
