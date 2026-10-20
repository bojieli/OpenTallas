#!/bin/bash
set -euo pipefail
mkdir -p src
tar xzf kit.tgz -C src
docker run --rm -v "$PWD/src:/src:ro" -v "$PWD:/out" -v /srv/opentallas-scratch/claude/ref_gate/dsdv_mu_hwin_c21j-20261020-013542/src:/frozen:ro -v /srv/opentallas-scratch/claude/ref_gate/dsdv_mu_hwin_c21j-20261020-013542/routes/gate/work/orfs/results/asap7/opentallas_dsdv_mu_hwin_capture_1019_asap7_ref_gate/base:/work:ro openroad/orfs:latest bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
args=()
for p in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*; do args+=(--liberty "$p"); done
args+=(--liberty /frozen/physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1_tt.lib)
python3 /src/tools/ref_tile/native_census.py --netlist /work/1_2_yosys.v --top dsdv_mu_hwin_capture_1019 --out /out/mandatory_native_census.json "${args[@]}" > /out/mandatory_native_census.log 2>&1
openroad -exit /out/stage_assign.tcl
'
