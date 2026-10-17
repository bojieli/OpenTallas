# Actual fixed S81 serial PLL /4 domain is0.9GHz; fast controller remains1.2GHz.
# Price: leaf264serial edges=352fast cycles, excluding80-beat prefetch/physical hops.
# Keep60/25ps uncertainty and all die IO/hold constraints; no timing exceptions.
if {$::ot_ref_pre_cts} {set hcx_period 1000.0} else {set hcx_period 1111.111111}
create_clock -name core_clk -period $hcx_period [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
if {!$::ot_ref_pre_cts} {set_propagated_clock [all_clocks]}
