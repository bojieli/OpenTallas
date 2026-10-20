#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/closure-loop/hidx_sel_s3d_a-s3da-db0cdd31d
A=$D/codex_clock_constant_0720
O=$(find "$D/routes" -path '*/base/6_final.odb' -print -quit)
sha256sum "$O" > "$A/before.sha256"
R=${O#$D/}
docker run --rm -v "$D:/job:ro" -v "$A:/audit" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit -python /audit/proof.py "/job/$R" /audit/output > "$A/proof.log" 2>&1
sha256sum -c "$A/before.sha256" > "$A/unchanged.log"
echo CLOCK_CONSTANT_AUDIT_DONE
