#!/bin/bash
set -euo pipefail
lane=$PWD
kit=$1
run=/srv/opentallas-scratch/claude/ref_gate/${kit}-20261020-024704
mkdir -p "$lane/$kit/out"
[ ! -f "$lane/$kit/reach.log" ] || cp "$lane/$kit/reach.log" "$lane/$kit/reach_previous_$(date -u +%Y%m%dT%H%M%S.%N).log"
docker run --rm -v "$run:/gate:ro" -v "$run/src:/src:ro" -v "$lane/audit_tools:/audit_tools:ro" -v "$lane/ring_reach.py:/audit.py:ro" -v "$lane/$kit/out:/out" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py > "$lane/$kit/reach.log" 2>&1
cat "$lane/$kit/reach.log"
