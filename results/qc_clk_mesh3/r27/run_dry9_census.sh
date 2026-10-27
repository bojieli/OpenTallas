#!/bin/bash
set -euo pipefail
test "$(git -C /srv/opentallas-scratch2/claude/wt/qc-infra-r27-1027 rev-parse --short=10 HEAD)" = 77c339e5bc
cd /srv/opentallas-scratch2/claude/qc-infra-r27/c_dry9a2
docker run --rm -e OT_V2_COLLECT_PLAN_ERRORS=1 --name r27-cdry9a2 --cpus=2 --memory=20g -v "/srv/opentallas-scratch2/claude/wt/qc-infra-r27-1027:/src:ro" -v "/srv/opentallas-scratch2/claude/qc-infra-r27/c_dry9a2:/work" openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /work; python3 /src/tools/die_plan/die_clock_mesh.py build inputs/plan.json --explicit-cells inputs/clock_spec.json --ndr 16w --libdir /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM --out build9 > build9.log 2>&1"; echo "rc $?"
echo R27_DRY9a_DONE $(date)
