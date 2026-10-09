read_db /work/results/asap7/opentallas_ot_qwen_die_hub_top_asap7_qdm_qfd_hub_ps_be5b56d78_tc_pin2_hm10_d2140/base/1_synth.odb
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
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 16} {
  set_io_pin_constraint -group -order -region right:4-62 -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 16-1}]]
}
set ot_region_pins [ot_match_pins {^x3_(v|d|tag|cr)(\[|$)}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 16} {
  set_io_pin_constraint -group -order -region right:64-120 -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 16-1}]]
}
set ot_region_pins [ot_match_pins {^ar_(v|d|cr)(\[|$)}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 16} {
  set_io_pin_constraint -group -order -region right:122-178 -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 16-1}]]
}
set ot_region_pins [ot_match_pins {^l3_(i|o)(\[|$)}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 16} {
  set_io_pin_constraint -group -order -region right:180-238 -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 16-1}]]
}
set ot_region_pins [ot_match_pins {^l0_(i|o)(\[|$)}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 16} {
  set_io_pin_constraint -group -order -region right:240-323 -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 16-1}]]
}
set ot_region_pins [ot_match_pins {^l1_(i|o)(\[|$)}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 16} {
  set_io_pin_constraint -group -order -region right:325-408 -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 16-1}]]
}
set ot_region_pins [ot_match_pins {^(ck|fck0|fck1|fck2|fck3|rst_n|fault)$}]
for {set ot_first 0} {$ot_first < [llength $ot_region_pins]} {incr ot_first 16} {
  set_io_pin_constraint -group -order -region top:100-300 -pin_names [lrange $ot_region_pins $ot_first [expr {$ot_first + 16-1}]]
}
place_pins -hor_layers {M4 M6} -ver_layers {M5 M7} -min_distance 1 -min_distance_in_tracks
set out [open /evidence/pins16.tsv w]
foreach t [[ord::get_db_block] getBTerms] {
foreach p [$t getBPins] { foreach b [$p getBoxes] {puts $out "[$t getName] [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]"} }
}
close $out
puts PIN_GROUP_CHECK_PASS
