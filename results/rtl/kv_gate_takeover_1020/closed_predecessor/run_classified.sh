#!/bin/bash
set -euo pipefail
lane=$PWD
kind=$1
case "$kind" in
 closed|negative) run=/srv/opentallas-scratch/claude/closure-loop/qkd_kvs_hroot_safe32-s32v3-e52c7bca5; odb=$(ls "$run"/routes/*/work/orfs/results/asap7/*/base/6_final.odb);;
 s32v4) run=/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_hroot_s32v4-20261020-041354; odb=$(ls "$run"/routes/gate/work/orfs/results/asap7/*/base/4_1_cts.odb);;
 s32v4b) run=/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_hroot_s32v4b-20261020-041356; odb=$(ls "$run"/routes/gate/work/orfs/results/asap7/*/base/4_1_cts.odb);;
 *) exit 2;;
esac
args=(); [ "$kind" != negative ] || args=(--clockload-negative)
mkdir -p "out_$kind"
docker image inspect openroad/orfs:latest --format '{{.Id}}' > "image_$kind.txt"
docker run --rm -v "$run:/route:ro" -v "$lane:/audit" -w /audit openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit/native_audit_v5_classified.py "${odb/$run/\/route}" "/audit/out_$kind" "${args[@]}"
