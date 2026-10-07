#!/bin/bash
# CLAUDE S81-RERUN dietop_round.sh <S81 real case dir (case a: floorplan.odb placed, k = 1)> <out dir> [threads] [mem_gb] [tile_um]
# S81 die-top FULL flow shake-out (coordinator audit 2026-10-07: no S81 die had a detailed route): the placed real case
# (every real / generated view LEF, die netlist at k = 1) -> coarse GRT tile (M2/M3 re-pitched, die signals on M4-M9;
# the HBM / Qwen die-top method) -> GRT -> DRT (M4-M9) -> antenna -> RCX (asap7 rcx_patterns.rules) -> SPEF; die STA SS/FF
# runs on the SPEF in a separate step once the view libs are assembled.  Every step checkpoints, logs OT_TIME / OTMEM;
# a failed step prints OT_STEP_FAIL and the flow continues where it can.
set -u
SR=$(readlink -f $1); D=$2; T=${3:-48}; M=${4:-700}; TILE=${5:-9.6}
mkdir -p $D; D=$(readlink -f $D)
cp $SR/*.lef $D/; ln -f $SR/floorplan.odb $D/placed.odb 2>/dev/null || cp $SR/floorplan.odb $D/placed.odb
cat > $D/dietop.tcl <<T
proc mem {tag} { set f [open /proc/self/status]; set s [read \$f]; close \$f
  regexp {VmRSS:\\s+(\\d+)} \$s -> r; regexp {VmHWM:\\s+(\\d+)} \$s -> h
  puts "OTMEM \$tag rss_mb=[expr {\$r/1024}] hwm_mb=[expr {\$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 \$body} err]} { puts "OT_STEP_FAIL \$name \$err"; flush stdout; return 0 }
  puts "OT_TIME step=\$name s=[format %.1f [expr {([clock milliseconds]-\$t0)/1000.0}]]"; mem \$name; flush stdout; return 1 }
set_thread_count $T
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f {q_elem.lef cfg.lef phy.lef serdes.lef ucie.lef elements.lef} { read_lef /work/\$f }
step load { read_db /work/placed.odb }
step coarse { set b [ord::get_db_block]; set p [expr {$TILE/15.0}]
  foreach ln {M2 M3} { odb::dbTrackGrid_destroy [\$b findTrackGrid [[ord::get_db_tech] findLayer \$ln]]
    make_tracks \$ln -x_offset 0.009 -x_pitch \$p -y_offset 0.009 -y_pitch \$p }
  puts "OT_TILE dbu=[\$b getGCellTileSize]" }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_*.lib*] { read_liberty \$l }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
step grt { global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt }
step guides { write_guides /work/route.guide }
step ckpt_grt { write_db /work/ckpt_grt.odb }
set ok_drt [step drt { detailed_route -bottom_routing_layer M4 -top_routing_layer M9 -output_drc /work/drt_drc.rpt -droute_end_iter 20 -verbose 1 }]
step ckpt_drt { write_db /work/ckpt_drt.odb }
step antenna { puts "OT_ANTENNA [check_antennas -report_file /work/antenna.rpt]" }
if {\$ok_drt} { step rcx { define_process_corner -ext_model_index 0 X; extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules; write_spef /work/die.spef } }
step wl { report_wire_length -net * -detailed_route -file /work/wirelength_drt.csv }
T
N=s81_dietop_$(basename $D)
date -u +%FT%TZ > $D/run.start
docker run --rm --name $N --cpus=$T --memory=${M}g -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/dietop.tcl > /work/dietop.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
echo $? > $D/run.exit; date -u +%FT%TZ > $D/run.end
