# Native register-slice W variant, four REAL kept forwarding inverter roots.
# Fail on a missing/ambiguous root. No clock groups, false paths or free cuts.
create_clock -name incoming -period 833.333 [get_ports fclk_i]
set stage_y [dict create]
foreach p [get_pins -hierarchical *] {
 set n [get_full_name $p]
 if {[regexp {g_stage\[([0-3])\].*u_fwd_inv.*/Y$} $n -> s]} {
  if {[dict exists $stage_y $s]} {error "ambiguous forwarded inverter root stage $s"}
  dict set stage_y $s $p
 }
}
if {[dict size $stage_y]!=4} {error "missing actual kept forwarded clock roots"}
set src [get_ports fclk_i];set master incoming
for {set s 0} {$s<4} {incr s} {
 set y [dict get $stage_y $s]
 create_generated_clock -name stage${s}_forwarded -source $src -master_clock $master -divide_by 1 -invert $y
 set_input_delay 166.666 -clock $master [get_ports [format {rst_n[%d]} $s]]
 set src $y;set master stage${s}_forwarded
}
create_generated_clock -name forwarded_output -source $src -master_clock $master -divide_by 1 [get_ports fclk_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_input_delay 166.666 -clock incoming [get_ports {i_v i_d*}]
set_output_delay 166.666 -clock forwarded_output -clock_fall [get_ports {o_v o_d*}]
set_max_fanout 32 [current_design]
