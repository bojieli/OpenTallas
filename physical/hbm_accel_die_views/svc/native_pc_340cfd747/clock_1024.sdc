# Actual native HBM period; no uncertainty or boundary relaxation.
set ot_hbm_period [expr {$::ot_ref_pre_cts ? 950.0 : 1024.0}]
create_clock -name core_clk -period $ot_hbm_period [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
if {!$::ot_ref_pre_cts} {set_propagated_clock [all_clocks]}
