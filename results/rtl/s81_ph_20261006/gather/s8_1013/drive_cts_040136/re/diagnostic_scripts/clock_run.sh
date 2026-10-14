#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/dsfd_gth_re-20261014-040136
docker run --rm -v "$R/routes/gate/work/orfs:/work:ro" -v "$R/src:/src:ro" -v "$PWD:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/clock_sinks.tcl > clock_sinks.log 2>&1
