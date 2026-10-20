#!/bin/bash
set -euo pipefail
src=$PWD/src;work=$PWD/work
img=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
# Intentionally only the canonical ORFS mapped-synthesis make target; never floorplan/CTS/layout.
docker run --rm --memory=48g --memory-swap=48g -e LEC_CHECK=0 -v "$src:/src:ro" -v "$PWD:/audit" -v "$work:/work" -w /OpenROAD-flow-scripts/flow --entrypoint bash "$img" -lc '
trap "chmod -R a+rwX /work >/dev/null 2>&1 || true" EXIT
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts
python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 /work/results/asap7/opentallas_ot_hgi_coll_gq_issue_asap7_ref_gate/base/1_2_yosys.v
python3 /audit/normalize.py
libs=(/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF* /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/*_tt.lib /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/*_ff.lib /src/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/*_tt.lib /src/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/*_ff.lib)
a=();for f in "${libs[@]}";do a+=(--liberty "$f");done
python3 /src/tools/ref_tile/native_census.py --netlist /work/results/asap7/opentallas_ot_hgi_coll_gq_issue_asap7_ref_gate/base/1_2_yosys.v --top ot_hgi_coll_gq_issue "${a[@]}" --out /work/native_census_r6.json
'
