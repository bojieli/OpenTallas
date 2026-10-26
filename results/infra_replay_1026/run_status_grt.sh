#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -exit /work/status_grt.tcl > "$D/status_grt.log" 2>&1
docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -python -exit /work/infra_replay.py --verify /work/status_after.odb --against /work/status_combined.replay.json > "$D/status_verify_v2.log" 2>&1
echo ACTUAL_ROUTED_TO_FIXED_GRT_PRESERVE_PASS
