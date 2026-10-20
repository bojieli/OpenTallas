#!/bin/bash
set -euo pipefail
A=$PWD
for n in hk1 hk1l; do
 case $n in hk1) t=062248;;hk1l)t=062247;;esac
 R=/srv/opentallas-scratch/claude/ref_gate/s81dvbk_sq_${n}-20261020-$t
 mkdir -p "$n"
 sha256sum "$R"/routes/gate/work/orfs/results/asap7/*/base/3_place.{odb,sdc} > "$n/checkpoint_before.sha256"
 for c in TT FF;do
 docker run --rm -e AUDIT_CORNER=$c -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work:ro" -v "$A:/audit:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/audit.tcl > "$n/${c}_ideal.log" 2>&1
 done
 sha256sum "$R"/routes/gate/work/orfs/results/asap7/*/base/3_place.{odb,sdc} > "$n/checkpoint_after.sha256"
 cmp "$n/checkpoint_before.sha256" "$n/checkpoint_after.sha256"
done
