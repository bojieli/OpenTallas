#!/bin/bash
# usage: dry.sh SRC PACKET  (PACKET holds plan.json + clock_spec.json)
set -euo pipefail
src=$1; packet=$2
cd "$packet"
docker run --rm --cpus=2 --memory=20g -e OT_V2_COLLECT_PLAN_ERRORS=1 -e OT_V2_BLOCKERS=1 -v "$src:/src:ro" -v "$packet:/work" openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /work; python3 /src/tools/die_plan/die_clock_mesh.py build plan.json --explicit-cells clock_spec.json --ndr 16w --libdir /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM --out build > build.log 2>&1"
echo QC_CLOCK_DRY_DONE
