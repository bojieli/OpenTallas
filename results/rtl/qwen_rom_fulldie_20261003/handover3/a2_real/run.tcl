# case (a): real-technology die floorplan, macro placement legality, on-track assert, pin access
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; puts "OTMEM $tag [expr {$r/1024}] MB [clock seconds]" }
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/phy_ew.lef
read_lef /work/elements.lef
read_verilog /work/die.v
link_design qfd_die
mem linked
initialize_floorplan -die_area {0 0 24156.144 32801.760} -core_area {0 0 24156.144 32801.760} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
set ::env(MAKE_TRACKS) /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
source /work/snap.tcl
mem floorplan
set t0 [clock seconds]
source /work/place.tcl
puts "OT_TIME place_s=[expr {[clock seconds]-$t0}]"
mem placed
# legality: every instance inside the die, no two macros overlap (sweep on x), lattice moves reported
set blk [ord::get_db_block]
set boxes {}
foreach inst [$blk getInsts] {
  set bb [$inst getBBox]
  lappend boxes [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax] [$inst getName]]
}
set boxes [lsort -integer -index 0 $boxes]
set n [llength $boxes]; set ov 0; set out 0
set dw [[$blk getDieArea] xMax]; set dh [[$blk getDieArea] yMax]
set active {}
foreach b $boxes {
  lassign $b x0 y0 x1 y1 nm
  if {$x0 < 0 || $y0 < 0 || $x1 > $dw || $y1 > $dh} { incr out; if {$out < 20} { puts "OT_OUTSIDE $nm" } }
  set keep {}
  foreach a $active {
    lassign $a ax0 ay0 ax1 ay1 an
    if {$ax1 > $x0} {
      lappend keep $a
      if {$ay0 < $y1 && $y0 < $ay1} { incr ov; if {$ov < 50} { puts "OT_OVERLAP $an $nm" } }
    }
  }
  lappend keep $b
  set active $keep
}
puts "OT_LEGAL instances=$n overlaps=$ov outside=$out"
write_def /work/floorplan_placed.def
mem def
if {[catch {ot_mts::assert_on_track -label fulldie} err]} { puts "OT_ASSERT FAIL $err" } else { puts "OT_ASSERT PASS" }
mem assert
set t0 [clock seconds]
set_routing_layers -signal M2-M9
if {[catch {pin_access -verbose 1} err]} { puts "OT_PA FAIL $err" } else { puts "OT_PA DONE" }
puts "OT_TIME pa_s=[expr {[clock seconds]-$t0}]"
mem pa
write_db /work/floorplan.odb
