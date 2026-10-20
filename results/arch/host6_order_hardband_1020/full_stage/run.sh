#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for v in a b; do
 kit=qkd_hr_core_order_n32$v
 mkdir -p "$PWD/$kit/out"
 docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' > "$PWD/$kit/image_id.txt"
 docker run --rm --cpus=2 --memory=16g -e AUDIT_KIT="$kit" -v "$PWD/$kit/gate:/gate:ro" -v "$PWD/$kit/gate/src:/src:ro" -v "$PWD/stage_identity.py:/audit.py:ro" -v "$PWD/$kit/out:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py > "$PWD/$kit/audit.log" 2>&1
 python3 analyze.py "$kit/out/stage_identity.json.gz" "$kit/analysis" >> "$kit/audit.log" 2>&1
done
