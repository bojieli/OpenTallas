# DIE-HEAD-60 11-04, from FWDCLK-1's hd_host_n_A_D trial (opt-in, nothing calls it by default). A routed DB built before
# 4d403f21b06 has forwarded-clock buffers with no input: TritonCTS reconnected one export per sink location. Connect each
# dead buffer to the clock net of a live export on the same source tap (landing_contract.json source_clock_port), route
# only that leaf net; all other metal stays. OT_FWD_NARROW_PINS (exact ports) applies the Rect Only pin form of
# prd_hook.tcl (dh59-prdpin) in the same DRT. Env: OT_FWD_IN, OT_FWD_CONTRACT, OT_FWD_OUT, THR; writes OT_FWD_OUT/{5_2_route.odb,eco_rcx.spef,eco_lec.v}.
read_db $::env(OT_FWD_IN)
set b [ord::get_db_block]; set t [ord::get_db_tech]
set o $::env(OT_FWD_OUT)
# contract: name -> tap, one line per clock output, from a small sidecar written by the driver
set fh [open $::env(OT_FWD_CONTRACT)]; set taps [dict create]
foreach l [split [read $fh] "\n"] { if {[llength $l] == 2} { dict lappend taps [lindex $l 1] [lindex $l 0] } }
close $fh
set grid [$b getGCellGrid]; set gx [$grid getGridX]; set gy [$grid getGridY]
proc snap {v g} { set lo [lindex $g 0]; set hi [lindex $g end]; foreach x $g { if {$x <= $v} {set lo $x}; if {$x > $v} {set hi $x; break} }; list $lo $hi }
set n_fixed 0; set leafs {}
dict for {tap ports} $taps {
  set dead {}; set live {}
  foreach p $ports {
    set in [$b findInst cland_fwd_$p]
    if {$in eq "NULL"} { error "OT_FWD no export buffer cland_fwd_$p" }
    set net [[$in findITerm A] getNet]
    if {$net eq "NULL"} { lappend dead $in } else { lappend live $net }
  }
  if {![llength $dead]} continue
  if {![llength $live]} { error "OT_FWD tap $tap has no live export (ports $ports): not this ECO's class" }
  set leaf [lindex $live 0]
  $leaf setDoNotTouch 0
  foreach in $dead {
    set dt [$in isDoNotTouch]; $in setDoNotTouch 0
    [$in findITerm A] connect $leaf
    $in setDoNotTouch $dt
    puts "OT_FWD connected [$in getName]/A -> [$leaf getName] tap $tap"
    incr n_fixed
  }
  # guides: the bbox of the leaf's guides and pins, snapped to GCells, on M2-M3 so the new pins join the old guide set
  set x0 1000000000; set y0 1000000000; set x1 -1000000000; set y1 -1000000000
  foreach g [$leaf getGuides] { set r [$g getBox]; set x0 [expr {min($x0,[$r xMin])}]; set y0 [expr {min($y0,[$r yMin])}]; set x1 [expr {max($x1,[$r xMax])}]; set y1 [expr {max($y1,[$r yMax])}] }
  foreach it [$leaf getITerms] { set r [$it getBBox]; set x0 [expr {min($x0,[$r xMin])}]; set y0 [expr {min($y0,[$r yMin])}]; set x1 [expr {max($x1,[$r xMax])}]; set y1 [expr {max($y1,[$r yMax])}] }
  set X0 [lindex [snap $x0 $gx] 0]; set X1 [lindex [snap $x1 $gx] 1]; set Y0 [lindex [snap $y0 $gy] 0]; set Y1 [lindex [snap $y1 $gy] 1]
  # M1 is via access only (DRT-0155): the M2 guide carries it as its via layer
  foreach {l v} {M2 M1 M3 M3} { odb::dbGuide_create $leaf [$t findLayer $l] [$t findLayer $v] [odb::new_Rect $X0 $Y0 $X1 $Y1] 0 }
  puts "OT_FWD leaf [$leaf getName] guide box $X0 $Y0 $X1 $Y1 ([expr {($X1-$X0)/1000.0}] x [expr {($Y1-$Y0)/1000.0}] (dbu/1000))"
  odb::dbWire_destroy [$leaf getWire]
  lappend leafs $leaf
}
puts "OT_FWD reconnected $n_fixed"
if {[info exists ::env(OT_FWD_NARROW_PINS)] && $::env(OT_FWD_NARROW_PINS) ne ""} {
  foreach pn $::env(OT_FWD_NARROW_PINS) {
    set bt [$b findBTerm $pn]
    if {$bt eq "NULL"} { error "OT_FWD_NARROW_PINS: no port $pn" }
    foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
      set ly [$bx getTechLayer]; set w [$ly getWidth]
      set a [$bx xMin]; set c [$bx xMax]; set d [$bx yMin]; set e [$bx yMax]
      if {[$ly getDirection] eq "VERTICAL"} {
        if {$c - $a <= $w} continue
        set m [expr {($a + $c) / 2}]; set a [expr {$m - $w / 2}]; set c [expr {$a + $w}]
      } else {
        if {$e - $d <= $w} continue
        set m [expr {($d + $e) / 2}]; set d [expr {$m - $w / 2}]; set e [expr {$d + $w}]
      }
      odb::dbBox_destroy $bx; odb::dbBox_create $bp $ly $a $d $c $e
      puts "OT_FWD narrow $pn [$ly getName] -> $a $d $c $e"
    } }
    set net [$bt getNet]; if {[$net getWire] ne "NULL"} { odb::dbWire_destroy [$net getWire] }
  }
}
if {[info exists ::env(DRY)]} { puts "OT_FWD guides ok, dry"; exit 0 }
set_thread_count $::env(THR)
detailed_route -output_drc $o/5_route_drc.rpt -output_maze $o/maze.log -verbose 1 -drc_report_iter_step 5
foreach l $leafs { puts "OT_FWD final [$l getName] wire [$l getWire]"; $l setDoNotTouch 1 }
check_antennas -report_file $o/drt_antennas.log
puts "OT_FWD routed [design_is_routed]"
write_db $o/5_2_route.odb
write_verilog $o/eco_lec.v
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules
write_spef $o/eco_rcx.spef
puts "OT_FWD_DONE"
