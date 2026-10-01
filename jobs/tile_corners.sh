#!/bin/bash
# usage: jobs/tile_corners.sh <keep-workdir> <DESIGN_NICKNAME>
# Sign-off corner STA of a routed W12 tile (AGENTS.md sign-off corners): setup at SS with 60 ps uncertainty,
# hold at FF with 25 ps, on the kept 6_final odb/sdc/spef, macros with their own _ss/_ff models; writes
# <keep>/corner_{ss,ff}.log (OTC lines), corner_ss_max.rpt, corner_ff_min.rpt and the SS end-point list.
set -o pipefail
K=$(readlink -f $1); N=$2
M=/src/physical/asap7_memory_macros
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
for C in SS FF; do
  c=$(echo $C | tr A-Z a-z)
  if [ $C = SS ]; then U="set_clock_uncertainty -setup 0.060 [all_clocks]"; else U="set_clock_uncertainty -hold 0.025 [all_clocks]"; fi
  cat > $K/orfs/corner_$c.tcl <<TCL
foreach f {asap7sc7p5t_AO_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_${C}_nldm_211120.lib.gz asap7sc7p5t_DFFHQNH2V2X_RVT_${C}_nldm_FAKE.lib asap7sc7p5t_DFFHQNV2X_RVT_${C}_nldm_FAKE.lib} { if {[file exists $L/\$f]} { read_liberty $L/\$f } }
read_liberty $M/ot_rom_4096x266_m8/ot_rom_4096x266_m8_${c}.lib
read_liberty $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_${c}.lib
read_db /work/results/asap7/$N/base/6_final.odb
read_sdc /work/results/asap7/$N/base/6_final.sdc
read_spef /work/results/asap7/$N/base/6_final.spef
set_propagated_clock [all_clocks]
set_clock_uncertainty 0 [all_clocks]
$U
puts "OTC setup_wns [sta::worst_slack_cmd max]"
puts "OTC hold_wns [sta::worst_slack_cmd min]"
puts "OTC setup_tns [sta::total_negative_slack_cmd max]"
puts "OTC hold_tns [sta::total_negative_slack_cmd min]"
puts "OTC reg2reg_setup_wns [sta::worst_slack_cmd max]"
report_checks -path_delay max -digits 1 -fields {slew cap fanout} > /work/corner_${c}_max.rpt
report_checks -path_delay min -digits 1 > /work/corner_${c}_min.rpt
report_checks -path_delay max -group_path_count 2000 -endpoint_path_count 1 -format end > /work/corner_${c}_ends.rpt
# --false-path-io routes: the in-tile segments (input pin -> first register, last register -> output pin) are
# the ends of the corridor wire stages; report them unconstrained so the stage budget can be checked
report_checks -unconstrained -from [all_inputs] -path_delay max -group_path_count 5000 -endpoint_path_count 1 -format end > /work/corner_${c}_in2reg.rpt
report_checks -unconstrained -to [all_outputs] -path_delay max -group_path_count 5000 -endpoint_path_count 1 -format end > /work/corner_${c}_reg2out.rpt
report_checks -unconstrained -from [all_inputs] -path_delay max -digits 1 > /work/corner_${c}_in2reg_worst.rpt
TCL
  docker run --rm -u $(id -u):$(id -g) -v $(pwd):/src:ro -v $K/orfs:/work openroad/orfs:latest bash -lc \
    "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash -threads 8 /work/corner_$c.tcl" > $K/corner_$c.log 2>&1
  grep OTC $K/corner_$c.log
done
