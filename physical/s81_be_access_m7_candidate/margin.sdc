# Actual legacy serial / stream clocks, preserved by this physical-only successor.
# No clock groups, reset release false paths, or blanket input hold false paths.
# io_ref_routed.sdc re-references each ot_lb_v_<real-clock> at its own measured
# corner's boundary mean after CTS and at final sign-off. Global drivers remain OPEN.
set ot_be_T [get_property [get_clocks core_clk] period]
create_clock -name str_clk -period [expr {$ot_be_T * 3.0 / 4.0}] [get_ports {cks*}]
create_clock -name ot_lb_v_core_clk -period $ot_be_T
create_clock -name ot_lb_v_str_clk -period [expr {$ot_be_T * 3.0 / 4.0}]
set_clock_uncertainty -setup 123 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ot_be_sin [get_ports {rns_in*}]
set ot_be_sout [get_ports {vrv* vrq*}]
set ot_be_cin {}
foreach p [all_inputs -no_clocks] { if {[lsearch -exact $ot_be_sin $p] < 0} { lappend ot_be_cin $p } }
set ot_be_cout {}
foreach p [all_outputs] { if {[lsearch -exact $ot_be_sout $p] < 0} { lappend ot_be_cout $p } }
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {domain inputs outputs frac} [list core_clk $ot_be_cin $ot_be_cout 1.0 str_clk $ot_be_sin $ot_be_sout 0.75] {
    set virtual [get_clocks ot_lb_v_$domain]
    set max_delay [expr {$ot_be_T * $frac * 0.2 + 90}]
    set_input_delay -max $max_delay -clock $virtual $inputs
    set_input_delay -min -50 -clock $virtual $inputs
    set_output_delay -max $max_delay -clock $virtual $outputs
    set_output_delay -min -50 -clock $virtual $outputs
}
