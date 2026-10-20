#!/bin/bash
set -u
b=$PWD
for q in 3 2; do
 old=$(ls -d /srv/opentallas-scratch/claude/ref_gate/hcoll_fj${q}_r128u3-20261020-023311)
 docker run --rm -v "$b:/audit" -v "$old:/old:ro" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
odb=$(find /old/routes/gate/work/orfs/results -name 5_1_grt.odb | head -1); echo ODB $odb
AUDIT_ODB="$odb" CELL_GRAPH=/audit/fj'"$q"'_native_graph_cells.tsv PORT_GRAPH=/audit/fj'"$q"'_native_graph_ports.tsv openroad -exit /audit/dump_native_graph_complete.tcl
libs=(/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib* /old/src/physical/asap7_memory_macros/ot_sram_1rw_128x64_m2_r2c2_p192_mir/*_tt.lib)
python3 /audit/native_odb.py '"$q"' "${libs[@]}"
echo NATIVE_RC=$?
AUDIT_ODB="$odb" AUDIT_PIN_REPORT=/audit/fj'"$q"'_pdn_missing.tsv openroad -exit /audit/protected_pg.tcl
' > "$b/fj${q}_postgrt_u3.log" 2>&1
 echo "FJ$q RC=$?"; grep -E "ODB|FAIL|PASS|NATIVE_RC|FJ_PROTECTED" "$b/fj${q}_postgrt_u3.log" | cut -c1-600
done
