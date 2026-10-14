# dsfd_engram_c PRE_DETAIL_PLACE (el1013-s81-engram 2026-10-13): each clock entry chain sits AT its child's clock pin.
# Global placement strings a chain along the line from the clock root to the pin, so an HB4xp67 drives 100+ um of wire
# (CTS-stop run c4: RSZ-3006 on u_hdly_ck_sink c[3], 293 ps slew at the sink pin without the chain).  Here every chain
# cell is moved onto its child's ck pin; detail placement legalises them in the nearest rows, so the chain nets are a
# few um, the delay is the cells' own, and the top tree's leaf lands at the child.
source /src/physical/s81_engc_tiles/compose/ck_entry_keep.tcl
set ot_cp_b [ord::get_db_block]; set ot_cp_k 0
foreach ot_m [$ot_cp_b getInsts] {
  if {![[$ot_m getMaster] isBlock]} { continue }
  set ot_it [$ot_m findITerm ck]
  if {$ot_it eq "NULL" || $ot_it eq ""} { continue }
  set ot_bb [$ot_it getBBox]
  set ot_x [expr {([$ot_bb xMin] + [$ot_bb xMax]) / 2}]; set ot_y [expr {([$ot_bb yMin] + [$ot_bb yMax]) / 2}]
  set ot_n [$ot_it getNet]; set ot_c 0
  while {$ot_n ne "NULL" && $ot_n ne ""} {
    set ot_d [$ot_n getFirstOutput]
    if {$ot_d eq "NULL" || $ot_d eq ""} { break }
    set ot_i [$ot_d getInst]
    if {![string match *u_hdly_ck_* [$ot_i getName]]} { break }
    $ot_i setLocation $ot_x $ot_y; $ot_i setPlacementStatus PLACED; incr ot_c; incr ot_cp_k
    set ot_n [[$ot_i findITerm A] getNet]
  }
  puts "OT_CK_ENTRY place: [$ot_m getName] ck pin ([expr {$ot_x / 1000.0}] [expr {$ot_y / 1000.0}]) chain $ot_c"
}
puts "OT_CK_ENTRY place: $ot_cp_k delay cells moved to their child's clock pin"
# Mapped ASAP7 reset/status flops expose QN and need an ordinary inverter
# for the RTL-positive value. Those inverter names are anonymous after ABC;
# moving only HDL-named flops leaves a long QN->INV->D path behind.
proc ot_engc_place_output_cone {seed x y} {
  set pending [list $seed]; set seen [dict create]; set moved 0
  while {[llength $pending]} {
    set inst [lindex $pending 0]; set pending [lrange $pending 1 end]
    set name [$inst getName]
    if {[dict exists $seen $name]} continue
    dict set seen $name 1
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
    incr moved
    foreach out [$inst getITerms] {
      if {[$out getIoType] ne "OUTPUT"} continue
      set net [$out getNet]
      if {$net eq "NULL" || $net eq ""} continue
      foreach load [$net getITerms] {
        if {[$load getIoType] ne "INPUT"} continue
        set next [$load getInst]; set master [$next getMaster]
        # Stop at the next register or hard child. Only transport/inversion
        # cells belong to this local output cone; shared reset-input trees do not.
        if {[$master isBlock] || ![regexp {^(INV|BUF|HB)} [$master getName]]} continue
        lappend pending $next
      }
    }
  }
  return $moved
}

# Resolve each relay bit to its actual hard-child destination pin through
# mapped inversion/transport cells. A bus-wide anchor is not enough when the
# parent's assigned pins span a long face.
proc ot_engc_relay_target {seed macro fallback_x fallback_y} {
  set pending [list $seed]; set seen [dict create]
  while {[llength $pending]} {
    set inst [lindex $pending 0]; set pending [lrange $pending 1 end]
    if {[dict exists $seen [$inst getName]]} continue
    dict set seen [$inst getName] 1
    foreach out [$inst getITerms] {
      if {[$out getIoType] ne "OUTPUT"} continue
      set net [$out getNet]
      if {$net eq "NULL" || $net eq ""} continue
      foreach load [$net getITerms] {
        if {[$load getIoType] ne "INPUT"} continue
        set next [$load getInst]
        if {$next eq $macro} {
          set bb [$load getBBox]
          return [list [expr {([$bb xMin]+[$bb xMax])/2}] [expr {([$bb yMin]+[$bb yMax])/2}]]
        }
        set master [$next getMaster]
        if {![$master isBlock] && [regexp {^(INV|BUF|HB)} [$master getName]]} { lappend pending $next }
      }
    }
  }
  # A retained constant/unused bit has no active output path.
  return [list $fallback_x $fallback_y]
}

# Local reset conditioners sit in legal rows beside each macro reset pin.
foreach ot_child {win io ws pb1 pb0 pb2 lkp sink} {
  set ot_macro [$ot_cp_b findInst u_$ot_child]
  set ot_rpin rst
  if {$ot_child in {lkp sink}} { set ot_rpin rst_n }
  set ot_rit [$ot_macro findITerm $ot_rpin]
  if {$ot_rit eq "NULL"} { error "ENGC reset pin absent: $ot_child/$ot_rpin" }
  set ot_bb [$ot_rit getBBox]
  set ot_x [expr {([$ot_bb xMin]+[$ot_bb xMax])/2}]
  set ot_y [expr {([$ot_bb yMin]+[$ot_bb yMax])/2}]
  set ot_found 0
  foreach ot_i [$ot_cp_b getInsts] {
    if {![string match *u_rst_${ot_child}* [$ot_i getName]]} continue
    ot_engc_place_output_cone $ot_i $ot_x $ot_y
    incr ot_found
  }
  if {$ot_found == 0} { error "ENGC reset conditioner absent: $ot_child" }
  puts "ENGC reset place $ot_child cells=$ot_found near ($ot_x,$ot_y)"
}

set ot_win [$ot_cp_b findInst u_win]
set ot_status_pin [$ot_win findITerm {s_rdy[0]}]
if {$ot_status_pin eq "NULL"} { error "ENGC WIN status pin absent" }
set ot_bb [$ot_status_pin getBBox]
set ot_x [expr {([$ot_bb xMin]+[$ot_bb xMax])/2}]
set ot_y [expr {([$ot_bb yMin]+[$ot_bb yMax])/2}]
set ot_status_cells 0
foreach ot_i [$ot_cp_b getInsts] {
  if {![string match *u_status_win* [$ot_i getName]]} continue
  lassign [ot_engc_relay_target $ot_i $ot_win $ot_x $ot_y] ot_tx ot_ty
  ot_engc_place_output_cone $ot_i $ot_tx $ot_ty
  incr ot_status_cells
}
if {$ot_status_cells < 16} { error "ENGC status stage cells missing" }
puts "ENGC status place cells=$ot_status_cells near WIN ready pin ($ot_x,$ot_y)"

set ot_pb0 [$ot_cp_b findInst u_pb0]
set ot_xpin [$ot_pb0 findITerm {w_oh[0]}]
if {$ot_xpin eq "NULL"} { error "ENGC PB0 transit pin absent" }
set ot_bb [$ot_xpin getBBox]
set ot_x [expr {([$ot_bb xMin]+[$ot_bb xMax])/2}]
set ot_y [expr {([$ot_bb yMin]+[$ot_bb yMax])/2}]
set ot_trans_cells 0
foreach ot_i [$ot_cp_b getInsts] {
  if {![string match *u_xtrans_pb0* [$ot_i getName]]} continue
  lassign [ot_engc_relay_target $ot_i $ot_pb0 $ot_x $ot_y] ot_tx ot_ty
  ot_engc_place_output_cone $ot_i $ot_tx $ot_ty
  incr ot_trans_cells
}
if {$ot_trans_cells < 334} { error "ENGC coherent transit registers missing" }
puts "ENGC transit place cells=$ot_trans_cells near PB0 write pin ($ot_x,$ot_y)"
