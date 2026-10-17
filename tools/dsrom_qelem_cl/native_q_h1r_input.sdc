# native_q_h1_input.sdc for the RSTP = 1 q element (QXPQ-RST 2026-10-17): rst_n drives only the synchronous reset relay
# flop's D pin (no asynchronous clear from the pin), so it is a data input like every other one and takes the same
# measured-virtual H1 minimum reference (sender + 50).  Max budgets, clock periods and uncertainties are unchanged.
if {[llength [get_clocks -quiet ot_lb_v_core_clk]] != 1} {
  error "Native Q H1 requires the measured ot_lb_v_core_clk reference"
}
set ot_nq_data [all_inputs -no_clocks]
unset_input_delay -min -clock [get_clocks core_clk] $ot_nq_data
set_input_delay -min 50 -clock [get_clocks ot_lb_v_core_clk] $ot_nq_data
puts "NATIVE_Q_H1R input_min=50 relative_to=measured_virtual reset_as_data=1"
