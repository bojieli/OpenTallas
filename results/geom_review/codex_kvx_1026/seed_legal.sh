#!/bin/bash
set -eu
K=$1
docker run --rm --memory=16g --cpus=8 -u "$(id -u):$(id -g)" -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; R=$(ls -d /work/run/results/asap7/*/base); printf "read_db %s/3_4_place_resized.odb\nset ::env(RESULTS_DIR) %s\nsource /work/face_flops.tcl\nwrite_db %s/3_4_place_resized.odb\n" "$R" "$R" "$R" > /work/seed.tcl; openroad -exit /work/seed.tcl; INPUT_ODB=$R/3_4_place_resized.odb OUTPUT_ODB=$R/3_4_place_resized.odb FACE_TABLE=$R/ot_face_flops.txt openroad -python -exit /work/legal_face_anchors.py; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 PRE_DETAIL_PLACE_TCL=/work/anchor_noop.tcl do-3_5_place_dp do-3_place'
