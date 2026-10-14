# Two actual synchronous PHY phase-family entries; no exceptions or multicycles.
# Both source slews declared150ps; actual die compensation remains a parent obligation.
set ot_tx_period [get_property [get_clocks core_clk] period]
create_clock -name tx_clk -period $ot_tx_period [get_ports ck_tx]
create_clock -name ot_lb_v_tx_clk -period $ot_tx_period
set_clock_uncertainty -setup 60 [get_clocks {tx_clk ot_lb_v_tx_clk}]
set_clock_uncertainty -hold 25 [get_clocks {tx_clk ot_lb_v_tx_clk}]
set_clock_transition 150 [get_clocks {core_clk tx_clk}]
# The generator budgets all predeclared data inputs before this secondary clock exists.
# Clear every clock-port data delay; all input data remain timed against the body clock.
unset_input_delay [get_ports {ck ck_tx}]
set ot_tx_ports [get_ports -quiet {tx_flit* tx_v}]
unset_output_delay $ot_tx_ports
set_output_delay 166.667 -max -clock ot_lb_v_tx_clk $ot_tx_ports
set_output_delay -50 -min -clock ot_lb_v_tx_clk $ot_tx_ports
# io_ref_routed read last maps exact ot_lb_v_tx_clk -> tx_clk corner boundary mean.
# Keep real core_clk <-> tx_clk setup/hold timing fully enabled.
