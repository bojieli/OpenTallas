# Die context (post-CTS only), as physical/qwen_slab_structural/io_ref.sdc: the register on the other side of every
# core port is a unit boundary register (ME spine / vector stream / stream, or the memory port register) in the same
# core clock region, balanced to the same insertion, so each boundary delay is referenced to the PROPAGATED clock of a
# register of this block's tree.  Setup keeps the 0.2 T outside budget (166.6 ps); hold credits nothing outside (0).
# OpenROAD 26Q3 crashes on -reference_pin (load_design; GRT layer assignment slack update), so the same reference is
# applied numerically: L = the propagated clock arrival at the reference register's CLK (measured here, after CTS),
# late arrival for launch / early for capture on setup, and the reverse on hold (pessimistic both ways).
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
# the gated engine clock (ICG output to the ME spine) is a clock, not a boundary data port
set qcc_outs {}
foreach p [all_outputs] { if {[get_full_name $p] ne "u_me.clk"} { lappend qcc_outs $p } }
set qcc_cells [get_cells {nx_v*}]
if {[llength $qcc_cells] == 0} { set qcc_cells [get_cells {pend1*}] }
set qcc_ref [get_pins "[get_full_name [lindex $qcc_cells 0]]/CLK"]
set qcc_w [sta::worst_slack_cmd max]
set qcc_lmax [get_property $qcc_ref arrival_max_rise]
set qcc_lmin [get_property $qcc_ref arrival_min_rise]
puts "QCC reference pin [get_full_name $qcc_ref] clock arrival max $qcc_lmax min $qcc_lmin"
set_input_delay [expr 166.6 + $qcc_lmax] -max -clock core_clk [all_inputs -no_clocks]
set_input_delay [expr 0 + $qcc_lmin] -min -clock core_clk [all_inputs -no_clocks]
set_output_delay [expr 166.6 - $qcc_lmin] -max -clock core_clk $qcc_outs
set_output_delay [expr 0 - $qcc_lmax] -min -clock core_clk $qcc_outs
