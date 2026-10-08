# SCREENING ONLY: calibrated leaf insertion, parent collective IO join unbound.
# Actual target frequency/uncertainties retained; no reset or data false paths.
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
sta::redirect_string_begin
report_clock_latency -clock core_clk
set ot_lat [sta::redirect_string_end]
if {![regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_lat -> ot_lo ot_hi]} {error "missing measured corner insertion: $ot_lat"}
set ot_L [expr {($ot_lo+$ot_hi)/2.0}]
create_clock -name vclk -period 833.333
set_clock_latency $ot_L [get_clocks vclk]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
puts "TRUECREDIT_SCREENING_INSERTION $ot_lo $ot_hi $ot_L PARENT_UNBOUND"
set ot_in [all_inputs -no_clocks]
catch {unset_input_delay $ot_in}
catch {unset_output_delay [all_outputs]}
set_input_delay -max 316.6666 -clock vclk $ot_in
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -max 316.6666 -clock vclk [all_outputs]
set_output_delay -min 0 -clock vclk [all_outputs]
set_input_transition 150 $ot_in
set_load 4 [all_outputs]
