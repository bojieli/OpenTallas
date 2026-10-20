#!/bin/bash
set -euo pipefail
lane=$PWD
kit=$1
run=/srv/opentallas-scratch/claude/ref_gate/${kit}-20261020-024704
mkdir -p "$lane/$kit/identity"
docker image inspect openroad/orfs:latest --format '{{.Id}}' > "$lane/$kit/identity/audit_image_id.txt"
docker run --rm -e AUDIT_KIT="$kit" -v "$run:/gate:ro" -v "$run/src:/src:ro" -v "$lane/audit_tools:/audit_tools:ro" -v "$lane/stage_identity.py:/audit.py:ro" -v "$lane/$kit/identity:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py > "$lane/$kit/identity.log" 2>&1
