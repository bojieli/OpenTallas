#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
I=/srv/opentallas-scratch2/claude/infra-physical-mesh-1026/mesh_connected_widthfinal.odb
docker run --rm -v "$D:/work" -v "$I:/old_input.odb:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /work/check_old_clearance.py > "$D/old_68via_clearance.log" 2>&1
