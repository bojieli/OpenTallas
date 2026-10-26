#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/hcoll_vmwrite_static_v6_roots_wmid-20261016-035819
C=$R/routes/gate/work/orfs
docker run --rm -v "$R/src:/src:ro" -v "$C:/work:ro" -v "$PWD:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/path_physical.tcl > path_physical.log 2>&1
