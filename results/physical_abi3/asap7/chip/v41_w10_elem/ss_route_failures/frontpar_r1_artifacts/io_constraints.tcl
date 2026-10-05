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
set_io_pin_constraint -group -order -region top:136.08-374.76 -pin_names [ot_match_pins {^(p|busy|fault|xs_q1|xs_e1).*}]
set_io_pin_constraint -group -order -region bottom:136.08-374.76 -pin_names [ot_match_pins {^(clk|rst|cfg|go|xs_v|xs_p|xs_b|xs_sv|xs_q0|xs_e0).*}]
