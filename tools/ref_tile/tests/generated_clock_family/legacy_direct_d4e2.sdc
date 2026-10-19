# PL-KIT direct D4/E2; diagnostic/adoption requires source-pinned native phase receipt.
set ot_lp_direct_T [get_property [get_clocks core_clk] period]
foreach a [get_clocks ot_entry_*] {
 foreach b [get_clocks ot_entry_*] {
  if {[get_full_name $a] eq [get_full_name $b]} continue
  set_clock_uncertainty -setup [expr {210.0 + 0.75 * $ot_lp_direct_T}] -from $a -to $b
  set_clock_uncertainty -hold 175.0 -from $a -to $b
 }
}
