#!/bin/bash
set -euo pipefail
lane=$PWD
run=/srv/opentallas-scratch/claude/closure-loop/qkd_kvs_hroot_s32v4-v4a-295504c93
odb=$(ls "$run"/routes/*/work/orfs/results/asap7/*/base/6_final.odb)
mkdir -p final_s32v4
sha256sum "$odb" > final_s32v4/input_before.sha256
docker image inspect openroad/orfs:latest --format '{{.Id}}' > final_s32v4/image.txt
docker run --rm -v "$run:/route:ro" -v "$lane:/audit" -w /audit openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit/native_audit_v5_classified_v2.py "${odb/$run/\/route}" /audit/final_s32v4
sha256sum "$odb" > final_s32v4/input_after.sha256
cmp final_s32v4/input_before.sha256 final_s32v4/input_after.sha256
