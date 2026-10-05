# Die context (post-CTS only), as physical/qwen_slab_structural/io_ref.sdc: the register on the other side of every
# core port is a unit boundary register (ME spine / vector stream / stream, or the memory port register) in the same
# core clock region, balanced to the same insertion, so each boundary delay is referenced to the PROPAGATED clock at a
# register of this block's tree (-reference_pin).  Setup keeps the 0.2 T outside budget (166.6 ps); hold credits
# nothing outside (-min 0).  Read AFTER load_design (a -reference_pin SDC crashes load_design).
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set qcc_cells [get_cells {nx_v*}]
if {[llength $qcc_cells] == 0} { set qcc_cells [get_cells {pend1*}] }
set qcc_ref [get_pins "[get_full_name [lindex $qcc_cells 0]]/CLK"]
puts "QCC reference pin [get_full_name $qcc_ref]"
set_input_delay 166.6 -max -clock core_clk -reference_pin $qcc_ref [all_inputs -no_clocks]
set_input_delay 0 -min -clock core_clk -reference_pin $qcc_ref [all_inputs -no_clocks]
set_output_delay 166.6 -max -clock core_clk -reference_pin $qcc_ref [all_outputs]
set_output_delay 0 -min -clock core_clk -reference_pin $qcc_ref [all_outputs]
