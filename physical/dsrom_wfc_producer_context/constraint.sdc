set_units -time ps -capacitance fF
create_clock -name core_clk -period 833.333333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
# Synthesis and pin-load extraction only. External launch/capture arcs remain open.
# No IO waiver, qualified STA, generated clock or timing-adoption claim.
