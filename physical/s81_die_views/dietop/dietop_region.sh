#!/bin/bash
# S81-DIE dietop_region.sh <die GRT dir (ckpt_grt.odb)> <sta kit dir> <name> <x0 y0 x1 y1 um> [threads] [mem_gb]
# REPRESENTATIVE-REGION detail route (OWNER STEER 2026-10-07 19:00: no flat full-die DRT).  The window is cut out of
# the die-level global-routed checkpoint: every instance wholly inside is kept at its die placement, everything else is
# removed; a net that also reached removed instances gets a boundary port (direction from its driver), placed by
# place_pins (HPWL to the inside pins, M4 on E/W edges, M5 on N/S).  The window is then globally routed with the die
# settings, detail routed (M4-M9, 64 iterations), antenna-checked and RCX-extracted.  Reported:
#   DRT convergence (violations per iteration), final DRC count, antenna
#   GRT-vs-DRT wire length per net (wirelength_grt.csv / wirelength_drt.csv)
#   GRT-vs-DRT timing: the same reg-to-reg STA (kit libs, clocks on the window's clock ports at the planned latency)
#   on GRT-estimated parasitics and on RCX parasitics -> per-endpoint slack delta (region_correlation.py)
set -u
G=$(readlink -f $1); K=$(readlink -f $2); N=$3; X0=$4; Y0=$5; X1=$6; Y1=$7; T=${8:-32}; M=${9:-200}
D=$G/region_$N; mkdir -p $D
SRC=$(cat $K/src_root)
cat > $D/region.tcl <<T
proc mem {tag} { set f [open /proc/self/status]; set s [read \$f]; close \$f
  regexp {VmRSS:\\s+(\\d+)} \$s -> r; regexp {VmHWM:\\s+(\\d+)} \$s -> h
  puts "OTMEM \$tag rss_mb=[expr {\$r/1024}] hwm_mb=[expr {\$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 \$body} err]} { puts "OT_STEP_FAIL \$name \$err"; flush stdout; return 0 }
  puts "OT_TIME step=\$name s=[format %.1f [expr {([clock milliseconds]-\$t0)/1000.0}]]"; mem \$name; flush stdout; return 1 }
set_thread_count $T
step load { read_db /g/ckpt_grt.odb }
step crop {
  set blk [ord::get_db_block]; set u [\$blk getDbUnitsPerMicron]
  set x0 [expr {round($X0*\$u)}]; set y0 [expr {round($Y0*\$u)}]; set x1 [expr {round($X1*\$u)}]; set y1 [expr {round($Y1*\$u)}]
  foreach bt [\$blk getBTerms] { odb::dbBTerm_destroy \$bt }
  set cut [dict create]; set kept 0; set gone 0
  foreach i [\$blk getInsts] {
    set b [\$i getBBox]
    if {[\$b xMin] >= \$x0 && [\$b yMin] >= \$y0 && [\$b xMax] <= \$x1 && [\$b yMax] <= \$y1} { incr kept; continue }
    foreach it [\$i getITerms] { set n [\$it getNet]; if {\$n ne "NULL" && ![\$n isSpecial]} { dict set cut [\$n getName] 1 } }
    odb::dbInst_destroy \$i; incr gone
  }
  set ports 0; set dropped 0
  foreach n [\$blk getNets] {
    if {[\$n isSpecial]} { continue }
    set its [\$n getITerms]
    if {[llength \$its] == 0} { odb::dbNet_destroy \$n; incr dropped; continue }
    if {![dict exists \$cut [\$n getName]]} { continue }
    set drv_in 0
    foreach it \$its { if {[\$it isOutputSignal]} { set drv_in 1 } }
    set bt [odb::dbBTerm_create \$n "p_[\$n getName]"]
    \$bt setIoType [expr {\$drv_in ? "OUTPUT" : "INPUT"}]
    incr ports
  }
  \$blk setDieArea [odb::new_Rect \$x0 \$y0 \$x1 \$y1]
  puts "OT_CROP kept=\$kept removed=\$gone ports=\$ports nets_dropped=\$dropped"
}
step pins { place_pins -hor_layers M4 -ver_layers M5 -corner_avoidance 1 -min_distance 2 -min_distance_in_tracks }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_SS_nldm_*.lib*] { read_liberty \$l }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
step grt { global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /r/grt_congestion.rpt }
step wl_grt { report_wire_length -net * -global_route -file /r/wirelength_grt.csv }
step spef_grt { estimate_parasitics -global_routing -spef_file /r/region_grt.spef }
step ckpt_grt { write_db /r/region_grt.odb }
set ok [step drt { detailed_route -output_drc /r/drt_drc.rpt -droute_end_iter 64 -verbose 1 }]
step ckpt_drt { write_db /r/region_drt.odb }
step antenna { puts "OT_ANTENNA [check_antennas -report_file /r/antenna.rpt]" }
step wl_drt { report_wire_length -net * -detailed_route -file /r/wirelength_drt.csv }
if {\$ok} { step rcx { define_process_corner -ext_model_index 0 X; extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules; write_spef /r/region_drt.spef } }
step netlist { write_verilog /r/region.v }
T
date -u +%FT%TZ > $D/run.start
docker run --rm --name s81_region_$N --cpus=$T --memory=${M}g -v $G:/g:ro -v $D:/r -w /r openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /r/region.tcl > /r/region.log 2>&1; rc=\$?; chmod -R a+rwX /r; exit \$rc"
echo $? > $D/run.exit
# timing correlation: same STA on both parasitics, per corner
python3 $SRC/tools/s81/region_correlation.py sta-tcl --kit $K --region $D > $D/sta_gen.log 2>&1
for c in ss ff; do for p in grt drt; do
  [ -f $D/region_$p.spef ] || continue
  docker run --rm --name s81_rsta_${N}_${c}_$p --cpus=4 -v $D:/r -v $K:/kit -v $SRC:$SRC:ro -w /r openroad/orfs:asap7lock \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; sta -no_init -exit /r/sta_${c}_$p.tcl > /r/sta_${c}_$p.log 2>&1; chmod a+rw /r/*" &
done; done
wait
python3 $SRC/tools/s81/region_correlation.py record --region $D --name $N --box $X0 $Y0 $X1 $Y1 > $D/record.log 2>&1
date -u +%FT%TZ > $D/run.end
