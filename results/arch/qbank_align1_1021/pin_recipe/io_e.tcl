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
ot_check_bus_complete [list {^(qb_row|qb_v|qb_beat|qb_full|qb_committed|qb_bad|dd_o|lcv_o|stage_o)(\[|$)} {^(dd_i|layer_context_v|command_stage|q_slot|q_slot_beat|ck|rst_n)(\[|$)}]
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
ot_check_pin_regions [list {^(qb_row|qb_v|qb_beat|qb_full|qb_committed|qb_bad|dd_o|lcv_o|stage_o)(\[|$)} {^(dd_i|layer_context_v|command_stage|q_slot|q_slot_beat|ck|rst_n)(\[|$)}]
set ot_region_pins [ot_match_pins {^(qb_row|qb_v|qb_beat|qb_full|qb_committed|qb_bad|dd_o|lcv_o|stage_o)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {1 + (517.4 - 1) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M3 M5} [expr {($ot_first / 1) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 561.6] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(dd_i|layer_context_v|command_stage|q_slot|q_slot_beat|ck|rst_n)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {1 + (517.4 - 1) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M3 M5} [expr {($ot_first / 1) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 0] -force_to_die_boundary
  incr ot_first
}
