set clk_period 833
create_clock -name core_clk -period $clk_period [get_ports ck]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
create_clock -name vclk -period [get_property [get_clocks core_clk] period]
set_clock_uncertainty -setup 123 [get_clocks {core_clk vclk}]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set_clock_latency 770 [get_clocks {core_clk vclk}]
set ot_in [all_inputs -no_clocks]
unset_input_delay -clock core_clk $ot_in
unset_output_delay -clock core_clk [all_outputs]
set_input_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk $ot_in
set_output_delay [expr {[get_property [get_clocks core_clk] period] * 0.2 + 150}] -clock vclk [all_outputs]
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -min 0 -clock vclk [all_outputs]
set ot_rst {}
foreach ot_c [get_cells *] { if {[string match {rst_s\[1\]*} [get_full_name $ot_c]]} { lappend ot_rst $ot_c } }
if {[llength $ot_rst]} { set_multicycle_path -setup 2 -from $ot_rst; set_multicycle_path -hold 1 -from $ot_rst }
