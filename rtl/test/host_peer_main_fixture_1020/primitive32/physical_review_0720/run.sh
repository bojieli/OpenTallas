#!/bin/bash
set -euo pipefail
for v in a b; do
 kit=qkd_hr_core_peer_p32$v
 gate=/srv/opentallas-scratch/claude/ref_gate/${kit}-20261020-050147
 mkdir -p "$PWD/$kit"
 docker image inspect openroad/orfs:latest --format '{{.Id}}' > "$PWD/$kit/image_id.txt"
 docker run --rm -e AUDIT_KIT="$kit" -v "$gate:/gate:ro" -v "$gate/src:/src:ro" -v "$PWD/stage_identity.py:/audit.py:ro" -v "$PWD/$kit:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py > "$PWD/$kit/audit.log" 2>&1
 python3 analyze.py "$kit/stage_identity.json.gz" "$kit/analysis" >> "$kit/audit.log" 2>&1
 done
