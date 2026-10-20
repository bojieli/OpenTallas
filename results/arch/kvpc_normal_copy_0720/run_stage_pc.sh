#!/bin/bash
set -euo pipefail
run=/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_pc_sr8-20261020-054430
mkdir -p stage_pc
# All source and placement inputs are read-only; no live gate files are written.
docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' > stage_pc/image_id.txt
docker run --rm -e AUDIT_KIT=qkd_kvs_pc_sr8 -v "$run:/gate:ro" -v "$run/src:/src:ro" -v "$run/src/tools/ref_tile:/audit_tools:ro" -v "$PWD/stage_identity_pc.py:/audit.py:ro" -v "$PWD/stage_pc:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /audit.py > stage_pc/identity.log 2>&1
