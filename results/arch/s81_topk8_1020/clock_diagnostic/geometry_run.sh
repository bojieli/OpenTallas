#!/bin/bash
set -euo pipefail
A=$PWD
for n in hk1 hk1l; do
 case $n in hk1)t=062248;;*)t=062247;;esac
 R=/srv/opentallas-scratch/claude/ref_gate/s81dvbk_sq_${n}-20261020-$t
 F=$(find "$R/routes/gate/work/orfs/results" -name 3_place.odb -print -quit)
 sha256sum "$F" > "$n/geometry_before.sha256"
 docker run --rm -v "$R/routes/gate/work/orfs:/work:ro" -v "$A:/audit" -e ODB_INPUT=/work/${F#"$R/routes/gate/work/orfs/"} -e OUT_JSON=/audit/$n/geometry.json.gz openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit -python /audit/geometry.py > "$n/geometry.log" 2>&1
 sha256sum "$F" > "$n/geometry_after.sha256"
 cmp "$n/geometry_before.sha256" "$n/geometry_after.sha256"
done
