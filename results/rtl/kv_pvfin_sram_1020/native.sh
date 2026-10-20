#!/bin/bash
set -eu
top=qkd_pv_fin_s32
docker run --rm -v "$PWD:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock make -B DESIGN_CONFIG=/work/results/rtl/kv_pvfin_sram_1020/$top.mk WORK_HOME=/work/native_$top synth >synth_$top.log 2>&1
for top in qkd_pv_fin_s32; do
 test -s native_$top/results/asap7/$top/base/1_2_yosys.v
 docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock python3 tools/ref_tile/native_census.py --netlist /work/native_$top/results/asap7/$top/base/1_2_yosys.v --top "$top" --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz --liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib --liberty /work/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_pvfin/ot_sram_1r1w_32x128_m1_p192_pvfin_tt.lib --out /work/results/rtl/kv_pvfin_sram_1020/native_${top}_census.json || true
done
