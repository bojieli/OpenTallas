#!/bin/bash
set -euo pipefail
lane=$PWD
for kind in s32v4 s32v4b; do
 case $kind in s32v4) stamp=041354;; s32v4b) stamp=041356;; esac
 run=/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_hroot_${kind}-20261020-${stamp}
 odb=$(ls "$run"/routes/gate/work/orfs/results/asap7/*/base/4_1_cts.odb)
 docker run --rm -v "$run:/gate:ro" -v "$lane:/audit" -w /audit openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit/register_inventory.py "${odb/$run/\/gate}" /gate "/audit/inventory_$kind"
done
