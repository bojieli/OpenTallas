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
ot_check_pin_regions [list {^(hub_i)(\\[|$)} {^(hub_o)(\\[|$)} {^(emb_i|emb_o)(\\[|$)} {^(kv_i|kv_o)(\\[|$)} {^(ck|lclk|rst_n|fault)(\\[|$)}]
set_io_pin_constraint -group -order -region left:* -pin_names [ot_match_pins {^(hub_i)(\\[|$)}]
set_io_pin_constraint -group -order -region right:* -pin_names [ot_match_pins {^(hub_o)(\\[|$)}]
set_io_pin_constraint -group -order -region top:* -pin_names [ot_match_pins {^(emb_i|emb_o)(\\[|$)}]
set_io_pin_constraint -group -order -region bottom:* -pin_names [ot_match_pins {^(kv_i|kv_o)(\\[|$)}]
set_io_pin_constraint -group -order -region left:* -pin_names [ot_match_pins {^(ck|lclk|rst_n|fault)(\\[|$)}]
