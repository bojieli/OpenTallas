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
set_io_pin_constraint -group -order -region left:* -pin_names [ot_match_pins {^in_}]
set_io_pin_constraint -group -order -region right:* -pin_names [ot_match_pins {^(local|out)_}]
