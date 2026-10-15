#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/dsfd_gth_rw-20261013-232924
docker run --rm -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work:ro" -v "/srv/opentallas-scratch/codex/s81-gather-dq-probe:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/s81-midpoint-assigned-probe.tcl > "/srv/opentallas-scratch/codex/s81-gather-dq-probe/assigned_probe.log" 2>&1
