set clk_period 833
create_clock -name core_clk -period $clk_period [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]
set_load 3.898 [all_outputs]
set_max_fanout 32 [current_design]
set_input_delay -min 0 -clock core_clk $non_clock_inputs
set_output_delay -min 0 -clock core_clk [all_outputs]

set ot_leaf_rst {}
foreach ot_c [get_cells -hierarchical -filter "ref_name == ot_attn_hgrp_m6h1"] {
  foreach ot_p [get_pins -of_objects $ot_c -filter "direction == input"] {
    if {[get_property $ot_p lib_pin_name] eq "rst_n"} { lappend ot_leaf_rst $ot_p }
  }
}
if {[llength $ot_leaf_rst] == 0} { error "leaf_reset_mcp: no leaf rst_n pins found" }
set_multicycle_path -setup 4 -to $ot_leaf_rst
set_multicycle_path -hold 3 -to $ot_leaf_rst
