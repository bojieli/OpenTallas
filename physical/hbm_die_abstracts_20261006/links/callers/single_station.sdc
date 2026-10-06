set actual_parent_file /src/physical/hbm_die_abstracts_20261006/links/callers/actual_parent_single_W2063.tcl
set expected_source_sha256 dcd1ec4292f5d9061b14a5ce79f50f8c1f939dae3ac9e21e4acf5970a009d49a
source /src/physical/hbm_die_abstracts_20261006/links/callers/parent_contract.tcl
create_clock -name incoming -period 833.333333 [get_ports fclk_i]
set roots {}
foreach pin [get_pins -hierarchical *] {
 if {[regexp {u_fwd_inv.*/Y$} [get_full_name $pin]]} {lappend roots $pin}
}
if {[llength $roots]!=1} {error "missing/ambiguous actual single station forwarding inverter"}
create_generated_clock -name forwarded -source [get_ports fclk_i] -master_clock incoming -divide_by 1 -invert [lindex $roots 0]
create_generated_clock -name output_root -source [lindex $roots 0] -master_clock forwarded -divide_by 1 [get_ports fclk_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
owner_input incoming [get_ports {rst_n i_v i_d*}]
owner_output output_root [get_ports {o_v o_d*}] 1
# fclk_o is an actual downstream clock-root port, not a zero-load timing cut.
if {![dict exists $parent_contract receiver_load_ui fclk_o]} {error "missing next-hop clock-tree root load"}
set_load [dict get $parent_contract receiver_load_ui fclk_o] [get_ports fclk_o]
set_max_fanout 32 [current_design]
