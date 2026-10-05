# Gated stage clock spine (2026-10-04): aon_clk is the always-on island's branch of the same stage clock (in the die
# both are taps of one root; here two ports so clock-tree synthesis builds the spine and the AO branch as separate
# trees, as the die does).  Same period and the same 60 ps setup / 25 ps hold uncertainty as core_clk, including
# the inter-clock paths (the AO side's replay / reset / isolation into the domain and the domain's busy back).
unset_input_delay -clock core_clk [get_ports aon_clk]
create_clock -name aon_clk -period $clk_period [get_ports aon_clk]
set_clock_uncertainty -setup 60 [get_clocks aon_clk]
set_clock_uncertainty -hold 25 [get_clocks aon_clk]
set_clock_uncertainty -setup 60 -from [get_clocks core_clk] -to [get_clocks aon_clk]
set_clock_uncertainty -setup 60 -from [get_clocks aon_clk] -to [get_clocks core_clk]
set_clock_uncertainty -hold 25 -from [get_clocks core_clk] -to [get_clocks aon_clk]
set_clock_uncertainty -hold 25 -from [get_clocks aon_clk] -to [get_clocks core_clk]
