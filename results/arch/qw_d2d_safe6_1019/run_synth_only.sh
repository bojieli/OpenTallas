#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/qw-d2d-safe6u-1019
mkdir -p "$R/native"
cp "$R/results/arch/qw_d2d_safe6_1019/synth_only.mk" "$R/native/config.mk"
docker run --rm -v "$R:/src:ro" -v "$R/native:/work" openroad/orfs:latest bash -lc 'cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth' > "$R/native/native_synth.log" 2>&1
