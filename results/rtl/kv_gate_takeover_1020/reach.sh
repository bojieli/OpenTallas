#!/bin/bash
set -euo pipefail
lane=$PWD
for v in s32v4 s32v4b; do
case $v in s32v4) stamp=20261020-023741;; s32v4b) stamp=20261020-023743;; esac
run=/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_hroot_${v}-$stamp
mkdir -p "$lane/$v/own_audit/tools/ref_tile" "$lane/$v/out"
cp textbook_lint.py "$lane/$v/own_audit/tools/ref_tile/"
cp native_census.py "$lane/$v/own_audit/tools/ref_tile/"
cp placed_reach_union.py "$lane/$v/"
docker run --rm -v "$run:/gate:ro" -v "$lane/$v/own_audit/tools/ref_tile:/audit_tools:ro" -v "$lane/$v/placed_reach_union.py:/audit.py:ro" -v "$lane/$v/out:/out" openroad/orfs:latest bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /audit.py' >"$lane/$v/reach.log" 2>&1
cat "$lane/$v/reach.log"
done
