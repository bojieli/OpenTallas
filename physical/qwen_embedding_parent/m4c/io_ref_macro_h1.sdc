# rule H1 (flow-hold 2026-10-07): the die-link hold term is carried once, by the sender output min; input min = L_min.
# Same policy as io_ref_skew.sdc; use the actual hard-macro clock port plus
# measured internal valid_q insertion. Never fall back to a payload FF.
source $embedding_binding_dir/clock_reference.tcl
set ref [get_pins -quiet u_ingress/clk]
if {[llength $ref] != 1} {error "expected real ingress macro clock pin u_ingress/clk"}
set unused [sta::worst_slack_cmd max]
set lmax [expr {[get_property $ref arrival_max_rise] + $embedding_ref_internal_setup_ps}]
set lmin [expr {[get_property $ref arrival_min_rise] + $embedding_ref_internal_hold_ps}]
puts "EMBED parent clock reference setup $lmax hold $lmin (macro port plus measured SS/FF internal insertion)"
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay [expr {166.667 + $lmax + 90}] -max -clock core_clk [all_inputs -no_clocks]
set_input_delay [expr {$lmin}] -min -clock core_clk [all_inputs -no_clocks]
set_output_delay [expr {166.667 - $lmax + 90}] -max -clock core_clk [all_outputs]
set_output_delay [expr {-$lmin - 50}] -min -clock core_clk [all_outputs]
set ins {};set outs {}
foreach pattern {i_* o_* fault} {
 foreach port [get_ports -quiet $pattern] {
  if {[get_property $port direction] eq "input"} {lappend ins $port} else {lappend outs $port}
 }
}
if {[llength $ins]} {set_input_delay [expr {166.667 + $lmax + 150}] -max -clock core_clk $ins}
if {[llength $outs]} {set_output_delay [expr {166.667 - $lmax + 150}] -max -clock core_clk $outs}
