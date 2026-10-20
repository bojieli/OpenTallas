#!/bin/bash
set -eu
R=$PWD
docker run --rm -v "$R/src:/src:ro" -v "$R/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > synth_v8.log 2>&1
cp work/results/asap7/opentallas_dsfd_coll_lane_w_safe4_asap7_ref_gate/base/1_2_yosys.v coll.v
python3 census.py > census_v8.log
python3 coll_depth.py > depth_v8.log
cat census_v8.log depth_v8.log
