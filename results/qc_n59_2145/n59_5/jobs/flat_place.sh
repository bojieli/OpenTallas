#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-n59-1026
K=$R/trial_flat/gen/native59
sudo docker run --rm --name codex-n59-flat-place --memory=32g --memory-swap=32g --cpus=16 -v "$K:/work" openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 REMOVE_ABC_BUFFERS=1 -o /work/run/results/asap7/dp_native59/base/1_synth.odb -o /work/run/results/asap7/dp_native59/base/2_floorplan.odb place
'
G=$R/trial_flat/geom;mkdir -p "$G"
S=/srv/opentallas-scratch2/claude/path-qc-n59-5i/geom
cp "$S/geometry_cones.py" "$S/summarize_geometry.py" "$S/station_moves_v2.json" "$S/classify.py" "$S/render.py" "$G/"
sudo docker run --rm --memory=8g -v "$K:/work:ro" -v "$G:/g" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit -python /g/geometry_cones.py /work/run/results/asap7/dp_native59/base/3_place.odb /g/all_geometry.json --all
python3 "$G/summarize_geometry.py" "$G/all_geometry.json" "$G/station_moves_v2.json" "$G/all_geometry.summary.json"
python3 "$G/classify.py" "$G/all_geometry.json" 30 > "$G/classify.txt"
python3 "$G/render.py" "$G/all_geometry.json" "$G/flat_actual.png" "N59 reset wrapper expansion + actual-graph data anchors: post-DPL"
