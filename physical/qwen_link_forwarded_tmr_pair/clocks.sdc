# ASAP7/OpenSTA units ps/fF. Same source-cycle launch/capture is the HOLD path;
# max path is the NEXT cycle. Do not introduce MCP/false paths/async groups.
create_clock -name ab_root -period 833.333333333 [get_ports clk_ab]
create_clock -name ba_root -period 833.333333333 -waveform {133.333333333 550} [get_ports clk_ba]
proc fwd_pin {stage direction} {
 set p {}
 foreach pin [get_pins -quiet -hierarchical *] {
  if {[string match "${stage}.*.${direction}.inv1.*.Y" [string map {/ .} [get_full_name $pin]]]} {lappend p $pin}
 }
 if {[llength $p] != 1} {error "forward clock pin not uniquely mapped: $stage/$direction: $p"}
 return $p
}
set ab1 [fwd_pin s0 ab]
set ab2 [fwd_pin s1 ab]
set ba1 [fwd_pin s1 ba]
set ba2 [fwd_pin s0 ba]
create_generated_clock -name ab_hop1 -source [get_ports clk_ab] -master_clock ab_root -divide_by 1 $ab1
create_generated_clock -name ab_hop2 -source $ab1 -master_clock ab_hop1 -divide_by 1 $ab2
create_generated_clock -name ba_hop1 -source [get_ports clk_ba] -master_clock ba_root -divide_by 1 $ba1
create_generated_clock -name ba_hop2 -source $ba1 -master_clock ba_hop1 -divide_by 1 $ba2
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set_clock_transition 50 [get_clocks {ab_root ba_root}]
# Fixture external budgets; production die endpoint timing is a separate gate.
set_input_delay -max 166.667 -clock ab_root [get_ports {a_i*}]
set_input_delay -min 50 -clock ab_root [get_ports {a_i*}]
set_input_delay -max 166.667 -clock ba_root [get_ports {b_i*}]
set_input_delay -min 50 -clock ba_root [get_ports {b_i*}]
set_output_delay -max 166.667 -clock ab_hop2 [get_ports {b_o*}]
set_output_delay -min -50 -clock ab_hop2 [get_ports {b_o*}]
set_output_delay -max 166.667 -clock ba_hop2 [get_ports {a_o*}]
set_output_delay -min -50 -clock ba_hop2 [get_ports {a_o*}]
# Reset is neither false-pathed nor case-disabled. Physical recovery/removal
# is reported under both external-root fixture windows, not declared closed.
foreach c {ab_root ba_root} {
 set_input_delay -add_delay -max 166.667 -clock $c [get_ports rst_n]
 set_input_delay -add_delay -min 50 -clock $c [get_ports rst_n]
}
set_input_transition 150 [get_ports {a_i* b_i* rst_n}]
set_load 80 [get_ports {a_o* b_o* clk_ab_o clk_ba_o}]
set_max_fanout 32 [current_design]
set_max_transition 260 [current_design]
