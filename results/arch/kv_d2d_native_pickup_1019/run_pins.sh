#!/bin/bash
set -e
for mode in ovl r7w; do
r=/srv/opentallas-scratch/claude/ref_gate/qkd_d2d_static_${mode}_s1-20261019-082412
f=$(find "$r/routes/gate/work/orfs/results" -name 4_cts.odb)
docker run --rm -v "$r:/r:ro" -v /tmp/kv_d2d_pins_1019.py:/audit.py:ro -e ODB="/r/${f#"$r/"}" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /audit.py > /tmp/kv_d2d_${mode}_pins_1019.json
done
