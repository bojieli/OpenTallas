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
set_io_pin_constraint -group -order -region bottom:20-195 -pin_names [ot_match_pins {^h_.*}]
set_io_pin_constraint -group -order -region top:20-195 -pin_names [ot_match_pins {^b_(v|rdy|addr|len|tag|we|wdata|wstrb|wr_done).*}]
set_io_pin_constraint -group -order -region top:210-370 -pin_names [ot_match_pins {^k_(v|rdy|addr|len|tag|we|wdata|wstrb|wr_done).*}]
set_io_pin_constraint -group -order -region bottom:210-370 -pin_names [ot_match_pins {^(k_grants|b_grants|contended)\[\d+\]$}]
set_io_pin_constraint -group -order -region left:5-12 -pin_names [ot_match_pins {^(clk|rst_n)$}]
