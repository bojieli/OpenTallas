#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
I=/srv/opentallas-scratch2/claude/infra-physical-mesh-1026/m89_ports/shared_audited_r1/infra.odb
docker run --rm -v "$D:/work" -v "$I:/input.odb:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /work/audit_low.py > "$D/audit.log" 2>&1
