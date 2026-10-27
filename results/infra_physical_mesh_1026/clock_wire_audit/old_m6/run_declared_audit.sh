#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
I=/srv/opentallas-scratch2/claude/infra-physical-mesh-1026/shared_m89_r3/infra.odb
if docker run --rm -v "$D:/work" -v "$I:/input.odb:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python -exit /work/infra_clock_audit.py --db /input.odb --clock-nets /work/clock_nets.txt --access-regions /work/old_access_regions_um.json --out /work/old_m6_audit_fail.json > "$D/old_m6_audit_fail.log" 2>&1; then echo OLD_M6_UNEXPECTED_PASS; exit 1; fi
grep -q "INFRA_CLOCK_AUDIT FAIL" "$D/old_m6_audit_fail.log"
echo OLD_M6_NATIVE_AUDIT_CORRECTLY_REJECTED
