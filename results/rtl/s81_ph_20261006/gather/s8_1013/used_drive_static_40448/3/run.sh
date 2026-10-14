#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/dsfd_gth_rw_clockleaf-20261014-044915
docker run --rm -v "$R/routes/gate/work/orfs:/work:ro" -v "$R/src:/src:ro" -v "$PWD:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/ss.tcl > ss.log 2>&1
docker run --rm -v "$R/routes/gate/work/orfs:/work:ro" -v "$R/src:/src:ro" -v "$PWD:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/ff.tcl > ff.log 2>&1
