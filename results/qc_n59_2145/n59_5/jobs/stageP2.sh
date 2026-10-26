#!/bin/bash
# PATH-QC-N59-5 stage P (place-only, no CTS/route) on intel2: kit = epyc1 path-qc-n59-5/gen/native59 after stage A
# (released run_kit.sh preflight PASS + floorplan) with the 3602 anchors installed (anchor_joint3 on rstB geometry,
# spread cap 120/10-um bin, all 3602 names found in this kit's netlist). ORFS place, then Codex complete-cone collector.
set -euo pipefail
R=/srv/opentallas-scratch2/claude/path-qc-n59-5i; K=$R/gen/native59; T=$R/tools
docker run --rm --name pathqc-n59-5-place --memory=32g --memory-swap=32g --cpus=16 -v $K:/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
 set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 -o /work/run/results/asap7/dp_native59/base/1_synth.odb -o /work/run/results/asap7/dp_native59/base/2_floorplan.odb place
 chown -R $HUID:$HGID /work/run'
G=$R/geom; mkdir -p $G; cp $T/codex-n59-2145-current3/{geometry_cones.py,summarize_geometry.py,station_moves_v2.json} $T/path-qc-n59-4/{classify.py,render.py} $G/
docker run --rm --memory=32g -v $K:/work -v $G:/g openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit -python /g/geometry_cones.py /work/run/results/asap7/dp_native59/base/3_place.odb /g/all_geometry.json --all
python3 -I $G/summarize_geometry.py $G/all_geometry.json $G/station_moves_v2.json $G/all_geometry.summary.json
python3 -I $G/classify.py $G/all_geometry.json 30 > $G/classify.txt
docker run --rm --memory=32g -v $G:/g openroad/orfs:asap7lock python3 -I /g/render.py /g/all_geometry.json /g/n59_5_combined.png "PATH-QC-N59-5 combined place" || echo RENDER_FAIL
echo STAGEP_DONE
