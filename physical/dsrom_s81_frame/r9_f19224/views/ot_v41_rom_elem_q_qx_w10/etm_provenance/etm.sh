#!/bin/bash
# CLAUDE S81-RERUN: extracted timing model (OpenSTA write_timing_model) of a routed block at SS and FF.
# usage: etm.sh <results_base_dir_with_6_final.{odb,spef,sdc}> <out_dir> <cell_name> [extra liberty glob]
set -u
B=$1; O=$2; CELL=$3; X=${4:-}
mkdir -p $O
grep -v -E "set_input_delay|set_output_delay|set_load|set_driving_cell|set_input_transition" $B/6_final.sdc > $O/etm.sdc
for C in SS FF; do
c=$(echo $C | tr A-Z a-z)
cat > $O/etm_$C.tcl <<TCL
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [glob \$L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*] { read_liberty \$f }
foreach f [glob -nocomplain $X] { if {[string match "*_${c}.lib" \$f]} { read_liberty \$f } }
read_db /b/6_final.odb
read_sdc /o/etm.sdc
read_spef /b/6_final.spef
set_propagated_clock [all_clocks]
write_timing_model -library_name ${CELL}_${c} /o/${CELL}_${c}.lib
puts "OT_ETM_DONE $C"
TCL
done
for C in SS FF; do
/srv/opentallas-scratch/admit.sh 16 -- docker run --rm --name etm_${CELL}_$C -v $B:/b:ro -v $O:/o -v /srv/opentallas-scratch/claude/s81-rerun/etm:/x:ro openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /o/etm_$C.tcl > /o/etm_$C.log 2>&1; chmod -R a+rwX /o"
done
