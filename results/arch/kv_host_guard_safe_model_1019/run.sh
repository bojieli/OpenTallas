#!/bin/bash
set -euo pipefail
root=/srv/opentallas-scratch/claude/ref_gate/qkd_hr_core_guard_frc-20261019-122000
odb=$root/routes/gate/work/orfs/results/asap7/opentallas_qkd_hr_core_guard_asap7_ref_gate/base
sha256sum "$odb/3_2_place_iop.odb" "$odb/5_1_grt.odb" > input_sha256.txt
docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' > image.txt
for f in 3_2_place_iop.odb 5_1_grt.odb; do
 docker run --rm --network none -e OMP_NUM_THREADS=2 -e ODBFILE="$f" -v "$root/src:/source:ro" -v "$odb:/odb:ro" -v "$PWD:/audit" openroad/orfs:asap7lock bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /audit/export.tcl' > "$f.export.log" 2>&1
done
