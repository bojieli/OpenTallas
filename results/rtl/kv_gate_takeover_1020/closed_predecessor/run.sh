#!/bin/bash
set -euo pipefail
lane=$PWD
run=/srv/opentallas-scratch/claude/closure-loop/qkd_kvs_hroot_safe32-s32v3-e52c7bca5
odb=$(ls "$run"/routes/*/work/orfs/results/asap7/*/base/6_final.odb)
mkdir -p out
docker image inspect openroad/orfs:latest --format '{{.Id}}' > image_id.txt
docker run --rm -v "$run:/route:ro" -v "$lane:/audit" -w /audit openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit/native_audit_v5.py "${odb/$run/\/route}" /audit/out
