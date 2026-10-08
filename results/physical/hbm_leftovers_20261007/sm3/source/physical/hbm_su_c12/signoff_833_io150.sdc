# HBM SU c12 vehicle sign-off at 833.333 ps WITH the agreed die IO budget (CLARIFICATION 2026-10-06): every data
# port 0.2T + 150 ps (die crossing to another clock region) against vclk at THIS corner's measured mean core_clk
# insertion, -min 0; resets false-pathed (quasi-static, synchronised at the receiver).  Replaces the route's
# false-path IO (corner_sta --post-sdc after the routed SDC).
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_propagated_clock [get_clocks core_clk]
catch {reset_path -from [all_inputs -no_clocks]}
catch {reset_path -to [all_outputs]}
catch {unset_input_delay [all_inputs -no_clocks]}
catch {unset_output_delay [all_outputs]}
sta::redirect_string_begin
report_clock_latency -clock core_clk
set ot_lat [sta::redirect_string_end]
if {![regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $ot_lat -> ot_lo ot_hi]} {error "no core_clk insertion: $ot_lat"}
set ot_L [expr {($ot_lo + $ot_hi) / 2.0}]
create_clock -name vclk -period 833.333
set_clock_latency $ot_L [get_clocks vclk]
puts "OT_VCLK_INSERTION $ot_lo $ot_hi $ot_L"
set ot_d [expr {0.2 * 833.333 + 150}]
set ot_in [all_inputs -no_clocks]
set ot_rst [get_ports -quiet {rst* *rst_n* por_n}]
set_input_delay -max $ot_d -clock vclk $ot_in
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -max $ot_d -clock vclk [all_outputs]
set_output_delay -min 0 -clock vclk [all_outputs]
if {[llength $ot_rst]} { set_false_path -from $ot_rst }
