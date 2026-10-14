#!/bin/bash
set -e
for stage in 1_synth 2_1_floorplan 3_3_place_gp 3_4_place_resized 4_1_cts; do
 docker run --rm -e CENSUS_STAGE="$stage" -v /srv/opentallas-scratch/claude/ref_gate/ot_qwen_tile_ctl_tp8_query40_resized-20261014-030918:/work:ro openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -no_init /work/q41_stage_census.tcl
done
