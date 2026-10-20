#!/bin/bash
set -eu
R=$PWD
B=/srv/opentallas-scratch/claude/ref_gate/s81ctrl_rg2_native32-20261020-013001
docker run --rm -v "$R:/audit" -v "$B:/case:ro" -v "$B/src:/src:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/dump.tcl > dump.log 2>&1
docker run --rm -v "$R:/audit" -v "$B/src:/src:ro" openroad/orfs:latest bash -lc '
args=(--netlist /audit/grt.v --top dsfd_ctrl_rg2 --out /audit/grt_actual_roles.json)
for lib in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib* /src/physical/asap7_memory_macros/ot_sram_1r1w2c_16x340_p192/ot_sram_1r1w2c_16x340_p192_tt.lib; do args+=(--liberty "$lib"); done
python3 /audit/tools/ref_tile/native_census.py "${args[@]}"
' > native.log 2>&1
