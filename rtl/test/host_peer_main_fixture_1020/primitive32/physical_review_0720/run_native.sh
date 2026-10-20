#!/bin/bash
set -euo pipefail
for v in a b; do
 kit=qkd_hr_core_peer_p32$v; gate=/srv/opentallas-scratch/claude/ref_gate/${kit}-20261020-050147
 mkdir -p "$PWD/$kit"
 docker run --rm -v "$gate:/gate:ro" -v "$PWD/native_reach.py:/audit.py:ro" -v "$PWD/$kit:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py > "$PWD/$kit/native_reach.log" 2>&1
 done
