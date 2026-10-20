#!/bin/bash
set -euo pipefail
lane=$PWD
for v in s32v4 s32v4b; do
case $v in s32v4) stamp=20261020-041354;; s32v4b) stamp=20261020-041356;; esac
run=/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_hroot_${v}-$stamp
mkdir -p "$lane/current_$v/own_audit/tools/ref_tile" "$lane/current_$v/out"
cp textbook_lint.py "$lane/current_$v/own_audit/tools/ref_tile/"
cp native_census.py "$lane/current_$v/own_audit/tools/ref_tile/"
cp placed_reach_union.py "$lane/current_$v/"
docker run --rm -v "$run:/gate:ro" -v "$lane/current_$v/own_audit/tools/ref_tile:/audit_tools:ro" -v "$lane/current_$v/placed_reach_union.py:/audit.py:ro" -v "$lane/current_$v/out:/out" openroad/orfs:latest bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py' >"$lane/current_$v/reach.log" 2>&1
cat "$lane/current_$v/reach.log"
done
