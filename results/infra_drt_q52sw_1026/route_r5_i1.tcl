# INFRA-FIRST-R5/DRT: q52sw crop (R4), fixes for R4 DR iteration-0 memory blow-up (~6 GB per worker):
#  (1) root cause: DRT inherits the GRT gcell grid; with kit M1-M3 tracks at 0.72 um GRT uses 10.8-um gcells, so a 7x7-gcell DR worker is
#      75.6 um square while M1-M3 are remade at 0.036 um -> ~2100 x 2100 track grid x 9 layers per worker. Fix: make the DRT M1-M3 tracks
#      BEFORE GRT so GRT/DRT gcells come from the real platform pitch.
#  (2) plan-side: the 35 M9 tap pins sit off the die M9 track grid (40 + 80k nm); snap each to its nearest track (<= 40 nm), as the plan must.
# MODE env OT_MODE = cgrt (kit tracks, coarse GRT only, baseline with snapped pins) | drt (fine tracks, GRT + DRT + RCX)
set mode $::env(OT_MODE)
set t0 [clock milliseconds]
read_db /src/q52sw.odb
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*] { read_liberty $f }
set blk [ord::get_db_block]; set tech [ord::get_db_tech]
set site NULL
foreach lib [[ord::get_db] getLibs] { set s [$lib findSite asap7sc7p5t]; if {$s != "NULL"} { set site $s } }
set da [$blk getDieArea]
set x0 [$da xMin]; set y0 [$da yMin]; set sw [$site getWidth]; set sh [$site getHeight]
set nm 0
foreach i [$blk getInsts] { if {![[$i getMaster] isBlock]} {
  set loc [$i getLocation]; set x [lindex $loc 0]; set y [lindex $loc 1]
  set r [expr {int(round(double($y-$y0)/$sh))}]; set x [expr {$x0 + int(round(double($x-$x0)/$sw))*$sw}]
  $i setPlacementStatus PLACED; $i setOrient [expr {$r%2 ? "MX" : "R0"}]; $i setLocation $x [expr {$y0+$r*$sh}]; $i setPlacementStatus FIRM; incr nm } }
puts "OT_STD_INSTS $nm"
# plan-side snap of tap pins to the die M8/M9 track grid (die origin 0: tracks at 40 + 80 k nm; crop x0/y0 are multiples of 80)
set nsnap 0; set dmax 0
foreach bt [$blk getBTerms] { foreach p [$bt getBPins] {
  set nb {}
  foreach b [$p getBoxes] { lappend nb [list [$b getTechLayer] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] }
  foreach b [$p getBoxes] { odb::dbBox_destroy $b }
  foreach e $nb { lassign $e l bx0 by0 bx1 by1
    if {[$l getDirection] eq "VERTICAL"} { set c [expr {($bx0+$bx1)/2}]; set n [expr {40 + int(round(($c-40)/80.0))*80}]; set d [expr {$n-$c}]; incr bx0 $d; incr bx1 $d
    } else { set c [expr {($by0+$by1)/2}]; set n [expr {40 + int(round(($c-40)/80.0))*80}]; set d [expr {$n-$c}]; incr by0 $d; incr by1 $d }
    if {$d != 0} { incr nsnap }; if {abs($d) > $dmax} { set dmax [expr {abs($d)}] }
    odb::dbBox_create $p $l $bx0 $by0 $bx1 $by1 } } }
puts "OT_PIN_SNAP moved $nsnap max_nm $dmax"
source /work/grt/tracks.tcl
proc fine_m13 {} {
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]
  foreach l {M1 M2 M3} { set tg [$blk findTrackGrid [$tech findLayer $l]]; if {$tg != "NULL"} { odb::dbTrackGrid_destroy $tg } }
  make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
  foreach yo {0.045 0.081 0.117 0.153 0.189 0.225 0.270} { make_tracks M2 -x_offset 0.009 -x_pitch 0.036 -y_offset $yo -y_pitch 0.270 }
  make_tracks M3 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
}
if {$mode eq "drt"} {
  # GRT tile = 15 x M1-M3 pitch: 0.144 -> 2.16-um gcells (0.036 -> 0.54 um aborted GRT-0228 edge usage; kit 0.72 -> 10.8 um = DR worker blow-up)
  foreach l {M1 M2 M3} { set tg [$blk findTrackGrid [$tech findLayer $l]]; if {$tg != "NULL"} { odb::dbTrackGrid_destroy $tg } }
  foreach l {M1 M2 M3} { make_tracks $l -x_offset 0.072 -x_pitch 0.144 -y_offset 0.072 -y_pitch 0.144 }
}
set_routing_layers -signal M8-M9
foreach {l a} {M4 0.75 M5 0.75 M6 0.75 M7 0.75 M8 0.4 M9 0.4} { set_global_routing_layer_adjustment $l $a }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_layer_rc -layer M8 -resistance 8.44765e-3 -capacitance [expr {.103962*1.3}]
set_layer_rc -layer M9 -resistance 8.89556e-3 -capacitance [expr {.0928446*1.3}]
set t1 [clock milliseconds]
global_route -congestion_iterations 50 -allow_congestion -verbose
set g [$blk getGCellGrid]; puts "OT_GCELL [llength [$g getGridX]] x [llength [$g getGridY]] pitch_nm [expr {[lindex [$g getGridX] 1]-[lindex [$g getGridX] 0]}]"
puts "OT_T grt [expr {[clock milliseconds]-$t1}] ms"
estimate_parasitics -global_routing -spef_file /d/i1/q52sw_${mode}_grt.spef
write_db /d/i1/q52sw_${mode}_grt.odb
if {$mode ne "drt"} { exit }
set_routing_layers -signal M1-M9
fine_m13
set t2 [clock milliseconds]
detailed_route -droute_end_iter 1 -output_drc /d/i1/q52sw_drc.rpt -verbose 1
puts "OT_T drt [expr {[clock milliseconds]-$t2}] ms"
set nr 0; set nn 0
foreach n [$blk getNets] { if {[$n getSigType] in {POWER GROUND}} continue; incr nn; if {[$n getWire] != "NULL"} { incr nr } }
puts "OT_NETS total $nn with_wire $nr"
write_db /d/i1/q52sw_routed.odb
extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules
write_spef /d/i1/q52sw_drt.spef
puts "OT_T total [expr {[clock milliseconds]-$t0}] ms"
