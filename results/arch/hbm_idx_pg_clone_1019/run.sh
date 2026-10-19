#!/bin/bash
set -euo pipefail
exec docker run --rm --entrypoint bash -v /srv/opentallas-scratch/claude/hbm-idx-pg-clone-1019:/proof -v /srv/opentallas-scratch/claude/closure-loop/hdie_col_idx256_1019-fan32g1-2727e1f68/routes/hdie_col_idx256_1019_fan32g1_2727e1f68:/route:ro openroad/orfs:latest -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /proof/clone_export.py'
