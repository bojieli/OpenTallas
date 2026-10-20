# std_band_fence.tcl (HBM-MC3G 10-20): band confinement for fill_reason.lattice_channel_bound kits.
# A literal-43.2 macro lattice leaves wide macro channels; the gate's measured_band_fill then requires every ordinary
# standard cell inside ONE full-width band (spec fill_reason.lattice_channel_bound.std_band_y_um) and lets only exact,
# approved pin / clock instances sit outside it.  Nothing in the flow put the cells there; this helper does, with a
# native OpenDB EXCLUSIVE region + group (the type GPL and DPL consume, physical/dscoll_cx/native_cell_fence.tcl).
#
# Env OT_BAND_Y = "lo:hi" (um, the spec band); the x span is the core area.  OT_BAND_CLOCK_PORTS (comma list, default
# clk) names clock ports whose nets never mark a cell as boundary.
#   ot_band_fence_create            PRE_GLOBAL_PLACE, AFTER the pin flops / hold stages are FIRM at their pins.
#                                   boundary = FIRM/LOCKED std cells + cells on a (non-clock) port net; members = every
#                                   other movable core cell + boundary cells already inside the band.
#                                   Writes RESULTS_DIR/ot_band_boundary.txt (boundary cells outside the band).
#   ot_band_fence_adopt STAGE       PRE_DETAIL_PLACE / POST_CTS: births since create (repair, hold, port buffers) join
#                                   the group and are seeded inside the band, EXCEPT boundary cells, port-net cells and
#                                   clock-net drivers (pin / clock roles, outside the band by design).
#   ot_band_fence_roles STAGE       writes RESULTS_DIR/ot_band_roles.json {boundary, clock} for the exception harvest
#                                   (tools/ref_tile/band_exception_harvest.py); layout_dump.tcl embeds it.
#   ot_band_fence_check STAGE       every group member inside the band (error otherwise).
# Not a timing, reach or PG waiver: the gate re-measures everything on the placed result.
global ot_band_name
set ot_band_name ot_std_band

proc ot_band_box {} {
  if {![info exists ::env(OT_BAND_Y)]} { error "OT_BAND: OT_BAND_Y (lo:hi um) not set" }
  set lh [split $::env(OT_BAND_Y) ":"]
  if {[llength $lh] != 2} { error "OT_BAND: OT_BAND_Y must be lo:hi, got $::env(OT_BAND_Y)" }
  lassign $lh lo hi
  set b [ord::get_db_block]
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  set c [$b getCoreArea]
  set y0 [expr {round($lo * $u)}]; set y1 [expr {round($hi * $u)}]
  if {!($y0 >= [$c yMin] && $y0 < $y1 && $y1 <= [$c yMax])} { error "OT_BAND: band $lo:$hi outside core" }
  return [list [$c xMin] $y0 [$c xMax] $y1]
}

# ordinary placeable standard cell (not a macro, tap/endcap/filler/decap, not FIXED)
proc ot_band_std {i} {
  set m [$i getMaster]
  if {[$m isBlock]} { return 0 }
  set ty [$m getType]
  if {$ty ne "CORE" && ![string match "CORE_*" $ty]} { return 0 }
  if {$ty in {CORE_WELLTAP CORE_SPACER CORE_ANTENNACELL} || [string match "ENDCAP*" $ty]} { return 0 }
  set mn [$m getName]
  if {[string match "TAPCELL*" $mn] || [string match "FILLER*" $mn] || [string match "DECAP*" $mn]} { return 0 }
  if {[$i getPlacementStatus] eq "FIXED"} { return 0 }
  return 1
}

proc ot_band_clock_ports {} {
  if {[info exists ::env(OT_BAND_CLOCK_PORTS)]} { return [split $::env(OT_BAND_CLOCK_PORTS) ","] }
  return {clk}
}

# cell with a pin on a port net (port buffers, pin flops, hold stages; clock ports excluded)
proc ot_band_on_port_net {i} {
  set cps [ot_band_clock_ports]
  foreach it [$i getITerms] {
    set n [$it getNet]
    if {$n eq "NULL" || [$n getSigType] in {POWER GROUND CLOCK}} continue
    foreach bt [$n getBTerms] {
      if {[$bt getSigType] ne "CLOCK" && [lsearch -exact $cps [$bt getName]] < 0} { return 1 }
    }
  }
  return 0
}

# cell whose output drives a clock net or a clock pin (CTS / spine buffers)
proc ot_band_clock_driver {i} {
  foreach it [$i getITerms] {
    if {![$it isOutputSignal]} continue
    set n [$it getNet]
    if {$n eq "NULL"} continue
    if {[$n getSigType] eq "CLOCK"} { return 1 }
    foreach l [$n getITerms] {
      if {[$l isInputSignal] && [[$l getMTerm] getSigType] eq "CLOCK"} { return 1 }
    }
  }
  return 0
}

proc ot_band_inside {i box} {
  lassign $box x0 y0 x1 y1
  set bb [$i getBBox]
  return [expr {[$bb xMin] >= $x0 && [$bb yMin] >= $y0 && [$bb xMax] <= $x1 && [$bb yMax] <= $y1}]
}

proc ot_band_boundary_file {} { return [file join $::env(RESULTS_DIR) ot_band_boundary.txt] }

proc ot_band_read_boundary {} {
  set s [dict create]
  set f [ot_band_boundary_file]
  if {![file exists $f]} { error "OT_BAND: missing $f (ot_band_fence_create did not run)" }
  set fh [open $f]
  foreach nm [split [read $fh] "\n"] { if {$nm ne ""} { dict set s $nm 1 } }
  close $fh
  return $s
}

proc ot_band_fence_create {} {
  global ot_band_name
  set b [ord::get_db_block]
  if {[$b findGroup $ot_band_name] ne "NULL" || [$b findRegion $ot_band_name] ne "NULL"} { error "OT_BAND: duplicate $ot_band_name" }
  set box [ot_band_box]
  set members {}; set boundary {}; set nb_in 0
  foreach i [$b getInsts] {
    if {![ot_band_std $i]} continue
    if {[$i getGroup] ne "NULL"} { error "OT_BAND: [$i getName] already owned by [[$i getGroup] getName]" }
    set bnd [expr {[$i getPlacementStatus] in {FIRM LOCKED COVER} || [ot_band_on_port_net $i]}]
    if {$bnd && ![ot_band_inside $i $box]} { lappend boundary [$i getName]; continue }
    if {$bnd} { incr nb_in }
    lappend members $i
  }
  if {[llength $members] == 0} { error "OT_BAND: no member cells" }
  lassign $box x0 y0 x1 y1
  set r [odb::dbRegion_create $b $ot_band_name]
  $r setRegionType EXCLUSIVE
  odb::dbBox_create $r $x0 $y0 $x1 $y1
  set g [odb::dbGroup_create $r $ot_band_name]
  $g setType VOLTAGE_DOMAIN
  foreach i $members { $g addInst $i }
  set fh [open [ot_band_boundary_file] w]
  puts $fh [join [lsort $boundary] "\n"]
  close $fh
  puts "OT_BAND_CREATED box_dbu=$box members=[llength $members] boundary_in_band=$nb_in boundary_outside=[llength $boundary]"
}

proc ot_band_fence_adopt {stage} {
  global ot_band_name
  set b [ord::get_db_block]
  set g [$b findGroup $ot_band_name]
  if {$g eq "NULL"} { error "OT_BAND: group $ot_band_name missing at $stage" }
  set box [ot_band_box]
  lassign $box x0 y0 x1 y1
  set bnd [ot_band_read_boundary]
  set n 0; set kept 0; set max_move 0
  foreach i [$b getInsts] {
    if {![ot_band_std $i] || [$i getGroup] ne "NULL"} continue
    if {[dict exists $bnd [$i getName]] || [ot_band_on_port_net $i] || [ot_band_clock_driver $i]} { incr kept; continue }
    if {[$i getPlacementStatus] ni {NONE UNPLACED SUGGESTED PLACED}} { error "OT_BAND: birth [$i getName] status [$i getPlacementStatus] at $stage" }
    $g addInst $i
    set bb [$i getBBox]
    set w [expr {[$bb xMax] - [$bb xMin]}]; set h [expr {[$bb yMax] - [$bb yMin]}]
    lassign [$i getLocation] ox oy
    set nx [expr {max($x0, min($x1 - $w, $ox))}]
    set ny [expr {max($y0, min($y1 - $h, $oy))}]
    set max_move [expr {max($max_move, abs($nx - $ox) + abs($ny - $oy))}]
    $i setLocation $nx $ny
    $i setPlacementStatus PLACED
    incr n
  }
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  puts "OT_BAND_ADOPT stage=$stage adopted=$n kept_out=$kept max_seed_move_um=[expr {$max_move / double($u)}]"
  return $n
}

proc ot_band_fence_check {stage} {
  global ot_band_name
  set g [[ord::get_db_block] findGroup $ot_band_name]
  if {$g eq "NULL"} { error "OT_BAND_CHECK missing group at $stage" }
  set box [ot_band_box]
  foreach i [$g getInsts] {
    if {![ot_band_inside $i $box]} { error "OT_BAND_CHECK outside cell=[$i getName] stage=$stage" }
  }
  puts "OT_BAND_CHECK_PASS stage=$stage members=[llength [$g getInsts]]"
}

proc ot_band_q {s} { return "\"[string map {\\ \\\\ \" \\\"} $s]\"" }

proc ot_band_fence_roles {stage} {
  global ot_band_name
  set b [ord::get_db_block]
  set box [ot_band_box]
  set bnd [ot_band_read_boundary]
  set pin {}; set clk {}
  foreach i [$b getInsts] {
    if {![ot_band_std $i] || [ot_band_inside $i $box]} continue
    set nm [$i getName]
    if {[dict exists $bnd $nm] || [ot_band_on_port_net $i]} { lappend pin [ot_band_q $nm] } elseif {[ot_band_clock_driver $i]} { lappend clk [ot_band_q $nm] }
  }
  set fh [open [file join $::env(RESULTS_DIR) ot_band_roles.json] w]
  puts $fh "{\"schema\": \"opentallas.band_roles.v1\", \"stage\": [ot_band_q $stage], \"band_y_um\": [ot_band_q $::env(OT_BAND_Y)],"
  puts $fh " \"pin\": \[[join $pin ", "]\],\n \"clock\": \[[join $clk ", "]\]}"
  close $fh
  puts "OT_BAND_ROLES stage=$stage pin=[llength $pin] clock=[llength $clk]"
}
