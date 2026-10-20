#!/bin/bash
set -eu
docker run --rm -v "$PWD/src:/src:ro" -v "$PWD/work:/work" -v "$PWD/admission:/admission:ro" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc '
args=(); for family in AO INVBUF OA SEQ SIMPLE; do for lib in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_${family}_RVT_SS_*.lib*; do args+=(--liberty "$lib"); done; done
args+=(--liberty /src/physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ss.lib --liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_128x32_m1/ot_sram_1r1w_128x32_m1_ss.lib)
python3 /admission/tools/ref_tile/native_census.py --netlist /work/results/asap7/opentallas_ot_v41_bf_col_asap7_ref_gate/base/1_2_yosys.v --top ot_v41_bf_col "${args[@]}" --out /work/actual_native_census.json
'
