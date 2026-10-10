read_db /work/results/asap7/opentallas_ot_qfd_res_ser_asap7_qdm_qfd_sp_res_ser_tsr41_942f13c8atc/base/1_synth.odb
initialize_floorplan -die_area {0 0 777.6 518.4} -core_area {2.16 2.16 775.44 516.24} -site asap7sc7p5t
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
ot_check_pin_regions [list {^(clk|rst_n|me_en)$} {^(i_ov|i_we|i_addr|i_mask)(\[|$)} {^i_data\[[0-9]*[02468]\]$} {^i_data\[[0-9]*[13579]\]$} {^(o_\w+|rok|fault)(\[|$)}]
set ot_region_pins [ot_match_pins {^(clk|rst_n|me_en)$}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {0 + (777.6 - 0) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M5 M7} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 518.4] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(i_ov|i_we|i_addr|i_mask)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {0 + (518.4 - 0) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^i_data\[[0-9]*[02468]\]$}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {0 + (518.4 - 0) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 0 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^i_data\[[0-9]*[13579]\]$}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {0 + (518.4 - 0) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M4 M6} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list 777.6 $ot_pos] -force_to_die_boundary
  incr ot_first
}
set ot_region_pins [ot_match_pins {^(o_\w+|rok|fault)(\[|$)}]
set ot_count [llength $ot_region_pins]
set ot_first 0
foreach ot_pin $ot_region_pins {
  set ot_pos [expr {0 + (777.6 - 0) * ($ot_first + 0.5) / $ot_count}]
  set ot_layer [lindex {M5 M7} [expr {($ot_first / 32) % 2}]]
  place_pin -pin_name $ot_pin -layer $ot_layer -location [list $ot_pos 0] -force_to_die_boundary
  incr ot_first
}

place_pins -hor_layers {M4 M6} -ver_layers {M5 M7} -min_distance 1 -min_distance_in_tracks
set out [open /evidence/pins.tsv w]
foreach t [[ord::get_db_block] getBTerms] {foreach p [$t getBPins] {foreach b [$p getBoxes] {puts $out "[$t getName] [[$b getTechLayer] getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax]"}}}
close $out
puts PIN_BALANCE_PASS
