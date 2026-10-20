#!/bin/bash
set -eu
q=$1; gate=$2; out=$PWD
img=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker run --rm -v "$out:/audit" -v "$gate:/frozen:ro" -w /OpenROAD-flow-scripts/flow --entrypoint bash "$img" -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
odb=$(find /frozen/routes/gate/work/orfs/results -name 5_1_grt.odb | head -1)
AUDIT_ODB="$odb" CELL_GRAPH=/audit/fj'"$q"'_native_graph_cells.tsv PORT_GRAPH=/audit/fj'"$q"'_native_graph_ports.tsv /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /audit/dump_native_graph_complete.tcl
libs=(/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib* /frozen/src/physical/asap7_memory_macros/ot_sram_1rw_128x64_m2_r2c2_p192_mir/*_tt.lib)
python3 /audit/native_odb.py '"$q"' "${libs[@]}"
'
