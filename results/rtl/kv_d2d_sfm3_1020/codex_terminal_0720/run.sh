#!/bin/bash
set -euo pipefail
lane=$PWD
for kind in r7w ovl; do
 run=/srv/opentallas-scratch/claude/ref_gate/qkd_d2d_static_${kind}_sfm3-20261020-025653
 odb=$(ls "$run"/routes/gate/work/orfs/results/asap7/*/base/5_1_grt.odb)
 mkdir -p "$kind"
 docker image inspect openroad/orfs:latest --format '{{.Id}}' > "$kind/image.txt"
 sha256sum "$odb" > "$kind/input.sha256"
 docker run --rm -v "$run:/route:ro" -v "$lane:/audit" -w /audit openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit/native_audit.py "${odb/$run/\/route}" "/audit/$kind"
done
