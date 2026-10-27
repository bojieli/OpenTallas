#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
docker run --rm -v "$D:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /work/infra_clock_audit.py --db /work/shared_audited_r1/infra.odb --clock-nets /work/clock_nets.txt --access-regions /work/access_regions.json --out /work/exact_centerline_audit.json > "$D/exact_centerline_audit.log" 2>&1
