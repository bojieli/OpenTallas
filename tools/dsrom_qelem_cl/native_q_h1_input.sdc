# Opt-in native Q H1 input reference; read only after the actual virtual clock
# has been refreshed from the current corner's boundary sinks. Max budgets,
# reset timing, clock periods and setup/hold uncertainties are unchanged.
if {[llength [get_clocks -quiet ot_lb_v_core_clk]] != 1} {
  error "Native Q H1 requires the measured ot_lb_v_core_clk reference"
}
set ot_nq_data {}
foreach p [all_inputs -no_clocks] {
  if {[get_full_name $p] ne "rst_n"} { lappend ot_nq_data $p }
}
unset_input_delay -min -clock [get_clocks core_clk] $ot_nq_data
set_input_delay -min 50 -clock [get_clocks ot_lb_v_core_clk] $ot_nq_data
puts "NATIVE_Q_H1 input_min=50 relative_to=measured_virtual reset_unchanged=1"
