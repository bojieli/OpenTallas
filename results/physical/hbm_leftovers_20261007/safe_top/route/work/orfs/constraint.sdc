set clk_period 730
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
set ot_L 566
set ot_T [get_property [get_clocks core_clk] period]
create_clock -name vclk -period $ot_T
set_clock_latency $ot_L [get_clocks {core_clk vclk}]
catch {unset_input_delay -clock core_clk [all_inputs -no_clocks]}
catch {unset_output_delay -clock core_clk [all_outputs]}
set ot_d [expr {0.2 * 833.333 + 150}]
set ot_in [all_inputs -no_clocks]
set_input_delay -max $ot_d -clock vclk $ot_in
set_input_delay -min -60 -clock vclk $ot_in
set_output_delay -max $ot_d -clock vclk [all_outputs]
set_output_delay -min 0 -clock vclk [all_outputs]
set ot_rst [get_ports -quiet {rst* *rst_n* por_n}]
if {[llength $ot_rst]} { set_false_path -from $ot_rst }
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ot_in
