#!/bin/bash
set -eu
W=$PWD
E=$W/results/rtl/kv_ectl_h15_1020
mkdir -p "$E/native"
docker run --rm -v "$W:/src:ro" -v "$E/native:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock make -B DESIGN_CONFIG=/src/results/rtl/kv_ectl_h15_1020/native.mk WORK_HOME=/work synth > "$E/native_synth.log" 2>&1
set +e
docker run --rm -v "$W:/src:ro" -v "$E/native:/work" -w /src openroad/orfs:asap7lock python3 tools/ref_tile/native_census.py --netlist /work/results/asap7/private_ectl_c_h15/base/1_2_yosys.v --top qkd_ectl_c_st_h15 --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz --out /work/native_census.json > "$E/native_census.log" 2>&1
rc=$?
set -e
cat "$E/native_census.log"
exit "$rc"
