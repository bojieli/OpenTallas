read_db /work/results/asap7/opentallas_ot_qwen_die_hub_top_asap7_qdm_qfd_hub_psp_be5b56d78_tc_pin2_hm10_d2140/base/1_synth.odb
initialize_floorplan -die_area {0 0 412.536 412.536} -core_area {2.16 2.16 410.376 410.376} -site asap7sc7p5t
source /evidence/make_tracks.tcl
# Written by tools/run_abi3_physical.py --pin-region.
proc ot_match_pins {pattern} {
  set names {}
  foreach bterm [[ord::get_db_block] getBTerms] {
    set name [$bterm getName]
    if {[regexp -- $pattern $name]} { lappend names $name }
  }
  if {[llength $names] == 0} { error "--pin-region $pattern matches no port" }
  return [lsort -dictionary $names]
}
proc ot_check_pin_regions {patterns} {
  set bad {}
  foreach bterm [[ord::get_db_block] getBTerms] {
    if {[lsearch -exact {POWER GROUND} [$bterm getSigType]] >= 0} { continue }
    set name [$bterm getName]
    set n 0
    foreach p $patterns { if {[regexp -- $p $name]} { incr n } }
    if {$n != 1} { lappend bad "$name:$n" }
  }
  if {[llength $bad] > 0} {
    error "--pin-regions-exhaustive: [llength $bad] ports match no region or more than one (port:matches): [lrange $bad 0 23]"
  }
}
ot_check_pin_regions [list {^l2_(i|o)(\[|$)} {^x3_(v|d|tag|cr)(\[|$)} {^ar_(v|d|cr)(\[|$)} {^l3_(i|o)(\[|$)} {^l0_(i|o)(\[|$)} {^l1_(i|o)(\[|$)} {^(ck|fck0|fck1|fck2|fck3|rst_n|fault)$}]
set ot_region_pins [ot_match_pins {^l2_(i|o)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {4 + (62 - 4) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 412.536 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^x3_(v|d|tag|cr)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {64 + (120 - 64) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 412.536 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^ar_(v|d|cr)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {122 + (178 - 122) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 412.536 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^l3_(i|o)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {180 + (238 - 180) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 412.536 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^l0_(i|o)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {240 + (323 - 240) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 412.536 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^l1_(i|o)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {325 + (408 - 325) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 412.536 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(ck|fck0|fck1|fck2|fck3|rst_n|fault)$}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {100 + (300 - 100) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M5 M7} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 412.536] -force_to_die_boundary
  incr ot_first
}

place_pins -hor_layers {M4 M6} -ver_layers {M5 M7} -min_distance 1 -min_distance_in_tracks
set out [open /evidence/pins_generated.tsv w]
foreach t [[ord::get_db_block] getBTerms] {
foreach p [$t getBPins] { foreach b [$p getBoxes] {puts $out "[$t getName] [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]"} }
}
close $out
puts PIN_GROUP_CHECK_PASS
