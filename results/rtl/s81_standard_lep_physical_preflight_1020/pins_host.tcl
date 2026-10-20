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
ot_check_bus_complete [list {^(lo0_v|lo0_r|lo0_d|li0_v|li0_r|li0_d|lo1_v|lo1_r|lo1_d|li1_v|li1_r|li1_d|rxv)(\[|$)} {^(l0_f)(\[|$)} {^(l1_f)(\[|$)} {^(l0_st)(\[|$)} {^(l1_st)(\[|$)} {^(clk)(\[|$)} {^(rst_n)(\[|$)} {^(t_host|t_kd|f_host|f_ks)(\[|$)} {^(sl_f)(\[|$)} {^(fault)(\[|$)} {^(f_lf)(\[|$)} {^(ro|ri)(\[|$)}]
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
ot_check_pin_regions [list {^(lo0_v|lo0_r|lo0_d|li0_v|li0_r|li0_d|lo1_v|lo1_r|lo1_d|li1_v|li1_r|li1_d|rxv)(\[|$)} {^(l0_f)(\[|$)} {^(l1_f)(\[|$)} {^(l0_st)(\[|$)} {^(l1_st)(\[|$)} {^(clk)(\[|$)} {^(rst_n)(\[|$)} {^(t_host|t_kd|f_host|f_ks)(\[|$)} {^(sl_f)(\[|$)} {^(fault)(\[|$)} {^(f_lf)(\[|$)} {^(ro|ri)(\[|$)}]
set ot_region_pins [ot_match_pins {^(lo0_v|lo0_r|lo0_d|li0_v|li0_r|li0_d|lo1_v|lo1_r|lo1_d|li1_v|li1_r|li1_d|rxv)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {1 + (560.6 - 1) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4} [expr {($ot_first / 1) % 1}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(l0_f)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {3 + (20 - 3) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4} [expr {($ot_first / 1) % 1}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(l1_f)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {3 + (20 - 3) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4} [expr {($ot_first / 1) % 1}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(l0_st)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {3 + (20 - 3) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4} [expr {($ot_first / 1) % 1}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(l1_st)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {3 + (20 - 3) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4} [expr {($ot_first / 1) % 1}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(clk)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {272.8 + (280.8 - 272.8) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4} [expr {($ot_first / 1) % 1}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(rst_n)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {280.8 + (288.8 - 280.8) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4} [expr {($ot_first / 1) % 1}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(t_host|t_kd|f_host|f_ks)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {1 + (474.2 - 1) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M3 M5} [expr {($ot_first / 1) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 0] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(sl_f)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {3 + (20 - 3) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M3 M5} [expr {($ot_first / 1) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 0] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(fault)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {3 + (20 - 3) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M3 M5} [expr {($ot_first / 1) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 0] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(f_lf)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {3 + (20 - 3) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M3 M5} [expr {($ot_first / 1) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 0] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(ro|ri)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {1 + (560.6 - 1) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4} [expr {($ot_first / 1) % 1}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 475.2 $ot_pos] -force_to_die_boundary
  incr ot_first
}
