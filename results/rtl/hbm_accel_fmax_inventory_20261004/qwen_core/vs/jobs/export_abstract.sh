#!/bin/bash
# Export the routed lane macro's abstract for the hierarchical SU top: LEF (write_abstract_lef) and corner ETMs
# (write_timing_model at SS and FF, from the routed ODB + SPEF + SDC) into <src>/physical/qwen_hbmacc_vs/<name>/.
# Usage: export_abstract.sh <route dir> <src snapshot dir> <macro name>
set -e
W=$1; SRC=$2; NAME=$3
ORFS=$W/work/orfs
BASE=$(cd $ORFS && ls -d results/asap7/*/base | head -1)
OUT=$SRC/physical/qwen_hbmacc_vs/$NAME; mkdir -p $OUT
P=/OpenROAD-flow-scripts/flow/platforms/asap7
for C in ss ff; do
  U=$(echo $C | tr a-z A-Z)
  LIBS=$(for l in AO_RVT_${U}_nldm_211120.lib.gz INVBUF_RVT_${U}_nldm_220122.lib.gz OA_RVT_${U}_nldm_211120.lib.gz SEQ_RVT_${U}_nldm_220123.lib SIMPLE_RVT_${U}_nldm_211120.lib.gz; do echo "read_liberty $P/lib/NLDM/asap7sc7p5t_$l"; done)
  cat > $OUT/export_$C.tcl <<TCL
$LIBS
read_db /input/$BASE/6_final.odb
read_sdc /input/$BASE/6_final.sdc
read_spef /input/$BASE/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd $( [ $C = ss ] && echo max || echo min )]"
write_timing_model -library_name ${NAME}_$C /out/${NAME}_$C.lib
write_abstract_lef -bloat_occupied_layers /out/$NAME.lef
puts OT_EXPORT_DONE
exit
TCL
  docker run --rm -v $ORFS:/input:ro -v $OUT:/out openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/export_$C.tcl > $OUT/export_$C.log 2>&1
  grep -q OT_EXPORT_DONE $OUT/export_$C.log
done
ls -la $OUT
