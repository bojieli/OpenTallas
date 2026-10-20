#!/bin/bash
set -euo pipefail
lane=$PWD
kit=$1
run=/srv/opentallas-scratch/claude/ref_gate/${kit}-20261020-024704
docker image inspect openroad/orfs:latest --format '{{.Id}}' > "$lane/$kit/out/audit_image_id.txt"
docker run --rm -v "$run:/gate:ro" -v "$run/src:/src:ro" -v "$lane/candidate_projection.py:/projection.py:ro" -v "$lane/inputs:/inputs:ro" -v "$lane/$kit/out:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /projection.py > "$lane/$kit/projection.log" 2>&1
