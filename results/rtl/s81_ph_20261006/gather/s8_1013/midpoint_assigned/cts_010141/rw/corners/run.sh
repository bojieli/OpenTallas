#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/dsfd_gth_rw-20261014-010141
docker run --rm -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work:ro" -v "$R/diagnostic_corners:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/tt.tcl > "$R/diagnostic_corners/tt.log" 2>&1
docker run --rm -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work:ro" -v "$R/diagnostic_corners:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/ss.tcl > "$R/diagnostic_corners/ss.log" 2>&1
docker run --rm -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work:ro" -v "$R/diagnostic_corners:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/ff.tcl > "$R/diagnostic_corners/ff.log" 2>&1
docker run --rm -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work:ro" -v "$R/diagnostic_corners:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/reach.tcl > "$R/diagnostic_corners/reach.log" 2>&1
