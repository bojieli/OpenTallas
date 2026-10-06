# Boundary delays referenced to the clock port (the form every ORFS stage loads and writes back): 0.2 x 833.333 each side.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay 166.667 -clock core_clk [all_inputs -no_clocks]
set_output_delay 166.667 -clock core_clk [all_outputs]
if {[llength [get_ports -quiet tile_id*]]} { set_false_path -from [get_ports tile_id*] }
