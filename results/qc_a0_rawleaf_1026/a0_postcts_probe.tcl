# PATH-QC 10-26 A0 raw leaf post-CTS probe (GEOM-REVIEW-10 23:48 conds 1-3): pin-reg insertion TT/FF, hold under legacy -40, reset-net buffers
set corner $::env(CORNER)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_${corner}_nldm*.lib*] { read_liberty $l }
read_db /work/run_ffpg/results/asap7/lsl_rawfault_m3/base/4_cts.odb
read_sdc /work/run_ffpg/results/asap7/lsl_rawfault_m3/base/4_cts.sdc
set_propagated_clock [all_clocks]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
sta::worst_slack_cmd max
set b [ord::get_db_block]
proc ck_at {c} { set p [get_pins -of_objects $c -filter "name==CLK"]; return [expr {[get_property $p arrival_max_rise]+0.0}] }
set all {}; set inr {}; set nfl {}; set inregs {}
foreach c [get_cells * -filter "ref_name=~DFF*"] { lappend all [ck_at $c] }
proc mean {l} { if {![llength $l]} {return 0}; return [expr {[tcl::mathop::+ {*}$l]/double([llength $l])}] }
# input-port regs and output (N flag) regs: one hop from ports through <=1 buffer
foreach p [all_inputs] { set n [get_full_name $p]; if {$n eq "clk"} continue
  foreach pin [get_pins -of_objects [get_nets [get_full_name $p]]] { set c [get_cells -of_objects $pin]
    set r [get_property $c ref_name]
    if {[string match DFF* $r]} { lappend inr [ck_at $c]; lappend inregs $c } elseif {[string match BUF* $r] || [string match INV* $r]} {
      foreach op [get_pins -of_objects $c -filter "direction==output"] { foreach sp [get_pins -of_objects [get_nets -of_objects $op] -filter "direction==input"] {
        set sc [get_cells -of_objects $sp]; if {[string match DFF* [get_property $sc ref_name]]} { lappend inr [ck_at $sc] } } } } } }
foreach p [all_outputs] {
  foreach pin [get_pins -of_objects [get_nets [get_full_name $p]]] { set c [get_cells -of_objects $pin]
    set r [get_property $c ref_name]
    if {[string match DFF* $r]} { lappend nfl [ck_at $c] } elseif {[string match BUF* $r] || [string match INV* $r]} {
      foreach ip [get_pins -of_objects $c -filter "direction==input"] { foreach dp [get_pins -of_objects [get_nets -of_objects $ip] -filter "direction==output"] {
        set dc [get_cells -of_objects $dp]; if {[string match DFF* [get_property $dc ref_name]]} { lappend nfl [ck_at $dc] } } } } } }
set m [mean $all]
puts [format "A0POSTCTS %s ff %d mean %.2f min %.2f max %.2f | in_regs %d mean %.2f (d %.2f) | out_regs %d mean %.2f (d %.2f)" $corner [llength $all] $m [tcl::mathfunc::min {*}$all] [tcl::mathfunc::max {*}$all] [llength $inr] [mean $inr] [expr {[mean $inr]-$m}] [llength $nfl] [mean $nfl] [expr {[mean $nfl]-$m}]]
# legacy IO contract: vclk bound to the pin-register mean, in_min -40, out_min 0 (60/25 uncertainty)
create_clock -name vclk -period 833
set_clock_latency -source [expr {([mean $inr]+[mean $nfl])/2.0}] [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set din {}; foreach p [all_inputs] { if {[get_full_name $p] ne "clk"} { lappend din $p } }
set_input_delay -max 166.6 -clock vclk $din; set_input_delay -min -40 -clock vclk $din
set_output_delay -max 166.6 -clock vclk [all_outputs]; set_output_delay -min 0 -clock vclk [all_outputs]
puts "A0HOLD $corner viol_min [sta::endpoint_violation_count min] viol_max [sta::endpoint_violation_count max]"
report_worst_slack -min -digits 2
report_worst_slack -max -digits 2
report_checks -path_delay min -group_path_count 2 -digits 2 -fields {input_pin}
set rn [get_nets -quiet u_mul.rst_n]; if {$rn eq ""} { set rn [get_nets -quiet *rst_n*] }
puts "A0RST nets [llength $rn]"
set bc 0; foreach n [$b getNets] { if {[string match *rst* [$n getName]]} { foreach it [$n getITerms] { if {[$it isOutputSignal] && [string match BUF* [[[$it getInst] getMaster] getName]]} { incr bc } } } }
puts "A0RST buffer-driven rst nets $bc"
foreach n [$b getNets] { if {[string match *rst* [$n getName]]} { set k [llength [$n getITerms]]; if {$k > 64} { puts "A0RST_FANOUT [$n getName] $k" } } }
