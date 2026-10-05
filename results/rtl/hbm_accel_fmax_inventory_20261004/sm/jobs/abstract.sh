#!/bin/bash
# Macro views of a routed leaf (for the SM element's hierarchical route): LEF abstract of the routed block
# (write_abstract_lef -bloat_occupied_layers) and its extracted timing models at SS and FF (write_timing_model on the
# routed odb + SPEF, clock propagated, NO clock uncertainty and NO I/O false paths, so every boundary arc is present;
# the parent applies the 60/25 ps policy once).  Views go to $R/src/physical/hbm_accel_sm_views/<top>/.
# Usage: abstract.sh <route label> <top>
R=/srv/opentallas-scratch/claude/hbm-fmax-sm
lab=$1; top=$2
W=$R/routes/$lab/work/orfs
V=$R/src/physical/hbm_accel_sm_views/$top
mkdir -p $V
base=$(ls -d $W/results/asap7/*/base | head -1)
rel=/work/${base#$W/}
PLAT=/OpenROAD-flow-scripts/flow/platforms/asap7
for c in ss ff tt; do
  C=$(echo $c | tr a-z A-Z)
  libs="asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz"
  {
    echo "read_lef $PLAT/lef/asap7_tech_1x_201209.lef"
    echo "read_lef $PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef"
    for l in $libs; do echo "read_liberty $PLAT/lib/NLDM/$l"; done
    echo "read_db $rel/6_final.odb"
    echo "read_spef $rel/6_final.spef"
    echo "create_clock -name clk -period 833 [get_ports clk]"
    echo "set_propagated_clock [all_clocks]"
    echo "write_timing_model -library_name ${top}_${c} /work/${top}_${c}.lib"
    [ $c = ss ] && echo "write_abstract_lef -bloat_occupied_layers /work/${top}.lef"
    echo "exit"
  } > $W/abs_$c.tcl
  docker run --rm -v $W:/work openroad/orfs:latest bash -lc \
    "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/abs_$c.tcl" > $W/abs_$c.log 2>&1
  cp $W/${top}_${c}.lib $V/
done
cp $W/${top}.lef $V/
ls -la $V
