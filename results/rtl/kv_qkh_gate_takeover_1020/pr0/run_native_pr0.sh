#!/bin/bash
set -eu
W=$PWD
mkdir -p native_work
# Source and current-main helpers read-only; output is a private synthesis-only image.
docker run --rm -v "$W/native_src:/src:ro" -v "$W/native_work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock make -B DESIGN_CONFIG=/src/pr0.mk WORK_HOME=/work synth > native_synth.log 2>&1
N=/work/results/asap7/private_lane8_pr0/base/1_2_yosys.v
test -s "native_work${N#/work}"
# Prove the logical bench used precisely the wrapper emitted by actual Yosys Tcl.
cmp ot_rst_land_wrapper.v native_work/results/asap7/private_lane8_pr0/base/ot_rst_land_wrapper.v
set +e
docker run --rm -v "$W/native_src:/src:ro" -v "$W/native_work:/work" -w /src openroad/orfs:asap7lock python3 tools/ref_tile/native_census.py --netlist "$N" --top ot_qkh_lane8_nc32c --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz --out /work/native_census.json > native_census.log 2>&1
census_rc=$?
set -e
printf '%s\n' "$census_rc" > native_census.exit
cat native_census.log
docker run --rm -v "$W/native_src:/src:ro" -v "$W/native_work:/work" -v "$W:/proof" -w /src openroad/orfs:asap7lock python3 /proof/review_pr0_boundary.py --source /src --netlist "$N" --native-report /work/native_census.json --out /work/boundary.json > boundary.log 2>&1
cat boundary.log
exit "$census_rc"
