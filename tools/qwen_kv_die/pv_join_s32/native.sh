#!/bin/bash
set -eu
top=ot_qwen_tp8_pv_join_s32_t
docker run --rm -v "$PWD:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock make -B DESIGN_CONFIG=/work/results/arch/kv_params4_pvj_1020/$top.mk WORK_HOME=/work/native_$top synth >synth_$top.log 2>&1
test -s native_$top/results/asap7/$top/base/1_2_yosys.v
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock python3 results/arch/kv_params4_pvj_1020/census_tool_snapshot/tools/ref_tile/native_census.py --netlist /work/native_$top/results/asap7/$top/base/1_2_yosys.v --top "$top" --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib  --out /work/results/arch/kv_params4_pvj_1020/native_${top}_census.json || true
