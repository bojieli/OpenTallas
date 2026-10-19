# Written by tools/run_abi3_physical.py --pin-region.
proc ot_pin_plain {name} { return [string map {\\\[ \[ \\\] \]} $name] }
proc ot_pin_base {name} { regsub {\[[0-9]+\]$} [ot_pin_plain $name] {} base; return $base }
proc ot_pin_matches {pattern name} {
  return [expr {[regexp -- $pattern $name] || [regexp -- $pattern [ot_pin_plain $name]] ||
                [regexp -- $pattern [ot_pin_base $name]]}]
}
proc ot_match_pins {pattern} {
  set names {}
  foreach bterm [[ord::get_db_block] getBTerms] {
    set name [$bterm getName]
    if {[ot_pin_matches $pattern $name]} { lappend names $name }
  }
  if {[llength $names] == 0} { error "--pin-region $pattern matches no port" }
  return [lsort -dictionary $names]
}
proc ot_check_bus_complete {patterns} {
  array set hit {}; array set all {}
  foreach bterm [[ord::get_db_block] getBTerms] {
    if {[lsearch -exact {POWER GROUND} [$bterm getSigType]] >= 0} { continue }
    set name [$bterm getName]
    set base [ot_pin_base $name]
    if {$base eq [ot_pin_plain $name]} { continue }
    incr all($base)
    foreach p $patterns { if {[ot_pin_matches $p $name]} { incr hit($base); break } }
  }
  set bad {}
  foreach base [array names hit] { if {$hit($base) != $all($base)} { lappend bad "$base:$hit($base)/$all($base)" } }
  if {[llength $bad] > 0} {
    error "--pin-region leaves bus bits unassigned (bus:assigned/bits): [lrange [lsort $bad] 0 23]"
  }
}
ot_check_bus_complete [list {^(a|b)(\[|$)} {^(y)(\[|$)} {^(clk|rst_n)(\[|$)}]
proc ot_check_pin_regions {patterns} {
  set bad {}
  foreach bterm [[ord::get_db_block] getBTerms] {
    if {[lsearch -exact {POWER GROUND} [$bterm getSigType]] >= 0} { continue }
    set name [$bterm getName]
    set n 0
    foreach p $patterns { if {[ot_pin_matches $p $name]} { incr n } }
    if {$n != 1} { lappend bad "$name:$n" }
  }
  if {[llength $bad] > 0} {
    error "--pin-regions-exhaustive: [llength $bad] ports match no region or more than one (port:matches): [lrange $bad 0 23]"
  }
}
ot_check_pin_regions [list {^(a|b)(\[|$)} {^(y)(\[|$)} {^(clk|rst_n)(\[|$)}]
set ot_region_pins [ot_match_pins {^(a|b)(\[|$)}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 32} {
  set_io_pin_constraint -group -order -region left:* -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 32 - 1}]]
}
set ot_region_pins [ot_match_pins {^(y)(\[|$)}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 32} {
  set_io_pin_constraint -group -order -region right:* -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 32 - 1}]]
}
set ot_region_pins [ot_match_pins {^(clk|rst_n)(\[|$)}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 32} {
  set_io_pin_constraint -group -order -region top:* -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 32 - 1}]]
}
