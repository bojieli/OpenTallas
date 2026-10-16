#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/hcoll_vmwrite_static_v6_roots_wmid-20261016-035819
C=$R/routes/gate/work/orfs
sha256sum $C/results/asap7/*/base/4_1_cts.odb $C/results/asap7/*/base/4_cts.sdc $R/src/physical/ref_tile/hcoll_vmwrite_static_v6_roots_wmid/signoff.sdc > inputs.sha256
for corner in tt ff; do
 docker run --rm -v "$R/src:/src:ro" -v "$C:/work:ro" -v "$PWD:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/out/meas_$corner.tcl" > "$corner.log" 2>&1
 grep 'PLACEMENT_DIAGNOSTIC' "$corner.log"
done
