# Opt-in DPL-only PREP. No routing, STA, RTL, source recipe or plan update.
# ROOT approval is required before setting OT_RELIEF_PREP=1 and executing.
foreach v {OT_RELIEF_PREP OT_RELIEF_ODB OT_RELIEF_SELECTION OT_RELIEF_OUT} {
  if {![info exists ::env($v)]} {error "missing $v"}
}
if {$::env(OT_RELIEF_PREP) ne "1"} {error "PREP execution not enabled"}
if {[file exists $::env(OT_RELIEF_OUT)]} {error "refuse existing output; retain prior verdicts"}
file mkdir $::env(OT_RELIEF_OUT)
read_db $::env(OT_RELIEF_ODB)
source $::env(OT_RELIEF_SELECTION)
set b [ord::get_db_block]
set u [expr {double([$b getDbUnitsPerMicron])}]
if {[llength [$b getInsts]] != 103954 || [llength [$b getNets]] != 101706} {error "wrong baseline graph"}
set expected_targets 141
if {[info exists ::env(OT_RELIEF_TARGET_COUNT)]} {
  if {$::env(OT_RELIEF_TARGET_COUNT) ni {140 141}} {error "unsupported reviewed target count"}
  set expected_targets $::env(OT_RELIEF_TARGET_COUNT)
}
if {[llength $relief_targets] != $expected_targets} {error "wrong finite target set"}
proc conn_sig {i} {
  set s {}
  foreach t [$i getITerms] {
    set n [$t getNet];set nn "NULL";if {$n ne "NULL"} {set nn [$n getName]}
    lappend s [list [[$t getMTerm] getName] $nn]
  }
  return [lsort $s]
}
proc pin_sig {b} {
  set s {}
  foreach t [$b getBTerms] {
    foreach p [$t getBPins] {foreach g [$p getBoxes] {
      lappend s [list [$t getName] [[$g getTechLayer] getName] [$g xMin] [$g yMin] [$g xMax] [$g yMax]]
    }}
  }
  return [lsort $s]
}
set pins_before [pin_sig $b]
set target_names {};set target_set [dict create]
foreach row $relief_targets {
  lassign $row name dx dy bx by master
  set i [$b findInst $name]
  if {$i eq "NULL" || [[$i getMaster] getName] ne $master} {error "target mismatch $name"}
  if {[$i getPlacementStatus] ne "PLACED"} {error "refuse originally fixed target $name"}
  if {[regexp {^(DFF|DHL|DLL|SDFF|ICG|CLK)} $master]} {error "refuse sequential/clock target $name"}
  foreach t [$i getITerms] {
    set n [$t getNet]
    if {$n ne "NULL" && [$n getSigType] eq "CLOCK"} {error "refuse clock/dummy target $name"}
  }
  set bb [$i getBBox]
  if {abs([$bb xMin]/$u-$bx) > 0.0002 || abs([$bb yMin]/$u-$by) > 0.0002} {error "stale target position $name"}
  if {abs(abs($dx)+abs($dy)-1.08) > 1e-9} {error "wrong seed bound"}
  lappend target_names $name;dict set target_set $name [list $dx $dy]
}
set saved [dict create]
foreach i [$b getInsts] {
  set name [$i getName]
  dict set saved $name [list [$i getLocation] [$i getOrient] [$i getPlacementStatus] [[$i getMaster] getName] [conn_sig $i]]
}
set rc [catch {
  # Lock every non-target instance: all FFs, clock drivers/dummies and other data.
  foreach i [$b getInsts] {
    if {![dict exists $target_set [$i getName]] && [$i getPlacementStatus] eq "PLACED"} {$i setPlacementStatus FIRM}
  }
  foreach name $target_names {
    set i [$b findInst $name]
    lassign [$i getLocation] x y;lassign [dict get $target_set $name] dx dy
    $i setLocation [expr {$x+round($dx*$u)}] [expr {$y+round($dy*$u)}]
  }
  # One extra site per side, only on the finite reviewed data targets.
  set_placement_padding -instances $target_names -left 1 -right 1
  # 1.08um seed + at most3.24um legalizer move = at most4.32um per axis.
  # This native Tcl wrapper accepts INTEGER MICRONS, then converts to
  # sites/rows internally. Use3um (stricter than3.24); the absolute
  #4.32um-from-original audit remains authoritative and fails closed.
  detailed_placement -max_displacement {3 3}
  check_placement -verbose
  if {[llength [$b getInsts]] != 103954 || [llength [$b getNets]] != 101706} {error "graph count changed"}
  if {[pin_sig $b] ne $pins_before} {error "port boxes changed"}
  set moved 0;set max_x 0.0;set max_y 0.0
  set audit [open "$::env(OT_RELIEF_OUT)/moves.tsv" w]
  puts $audit "instance\told_x_um\told_y_um\tnew_x_um\tnew_y_um\tdx_um\tdy_um"
  foreach i [$b getInsts] {
    set name [$i getName];lassign [dict get $saved $name] oldloc oldori oldstatus oldmaster oldconn
    if {[[$i getMaster] getName] ne $oldmaster || [conn_sig $i] ne $oldconn} {error "logical graph changed $name"}
    set loc [$i getLocation];lassign $loc nx ny;lassign $oldloc ox oy
    if {![dict exists $target_set $name]} {
      if {$loc ne $oldloc || [$i getOrient] ne $oldori} {error "non-target moved $name"}
    } else {
      set dx [expr {abs($nx-$ox)/$u}];set dy [expr {abs($ny-$oy)/$u}]
      if {$dx>4.3201 || $dy>4.3201} {error "scope displacement exceeded $name"}
      if {$dx>0 || $dy>0} {incr moved}
      set max_x [expr {max($max_x,$dx)}];set max_y [expr {max($max_y,$dy)}]
      puts $audit [join [list $name [expr {$ox/$u}] [expr {$oy/$u}] [expr {$nx/$u}] [expr {$ny/$u}] $dx $dy] \t]
    }
  }
  close $audit
  if {$moved==0} {error "no changed placement; do not reroute identical geometry"}
} err opts]
# Restore the original placement-status contract in both successful and failed PREP.
foreach i [$b getInsts] {
  if {[dict exists $saved [$i getName]]} {$i setPlacementStatus [lindex [dict get $saved [$i getName]] 2]}
}
if {$rc} {
  set f [open "$::env(OT_RELIEF_OUT)/FAIL.txt" w];puts $f $err;close $f
  write_db "$::env(OT_RELIEF_OUT)/prep-failed.odb"
  return -options $opts $err
}
check_placement -verbose
write_db "$::env(OT_RELIEF_OUT)/local_relief_prep.odb"
set f [open "$::env(OT_RELIEF_OUT)/PREP.txt" w]
puts $f "DPL-only PREP: moved $moved/$expected_targets data cells; max_axis_um $max_x $max_y; all non-target geometry/pins/graph preserved. No GRT/STA/DRT PASS."
close $f
