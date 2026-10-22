#!/bin/bash
# RTLGAP-SUKV pre-gate native census of ot_s81sl_cmp_pool (ORFS asap7lock synth -> tools/ref_tile/native_census.py,
# limit 32 loads a driver, no waiver).  Run from the source root (it is mounted at /work).
set -eu
top=ot_s81sl_cmp_pool
docker run --rm -v "$PWD:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock make -B DESIGN_CONFIG=/work/tools/s81_dv/rtlgap_sukv_1021/pool_census.mk WORK_HOME=/work/native_$top synth >synth_$top.log 2>&1
test -s native_$top/results/asap7/$top/base/1_2_yosys.v
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock python3 tools/ref_tile/native_census.py --netlist /work/native_$top/results/asap7/$top/base/1_2_yosys.v --top "$top" --liberty $L/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz --liberty $L/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz --liberty $L/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz --liberty $L/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz --liberty $L/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib --out /work/native_${top}_census.json || true
ls -la native_${top}_census.json
