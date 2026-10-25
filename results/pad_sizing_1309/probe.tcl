set corner $::env(CORNER)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${corner}_nldm_*.lib*] {read_liberty $f}
read_db /head/run/results/asap7/dp_hd_turn_a/base/6_final.odb
read_sdc /head/run/results/asap7/dp_hd_turn_a/base/6_final.sdc
read_spef /head/run/results/asap7/dp_hd_turn_a/base/6_final.spef
set_propagated_clock [get_clocks clk]
sta::worst_slack_cmd max
set block [ord::get_db_block]
puts "PROBE_CORNER $corner"
foreach i [$block getInsts] {
 set name [$i getName]
 if {![string match ot_prp_d* $name]} continue
 set outs {};set ins {}
 foreach it [$i getITerms] {
  if {[$it isOutputSignal]} {lappend outs $it}
  if {[$it isInputSignal]} {lappend ins $it}
 }
 if {[llength $outs]!=1 || [llength $ins]!=1} {error "Pad has non-simple pins $name"}
 set o [lindex $outs 0];set a [lindex $ins 0];set n [$o getNet]
 puts "PAD $name [[$i getMaster] getName] NET [$n getName]"
 foreach it [$n getITerms] {
  if {![$it isInputSignal]} continue
  puts "LOAD $name [[$it getInst] getName] [[[$it getInst] getMaster] getName] [[$it getMTerm] getName]"
 }
 report_net [$n getName]
 report_dcalc -from [get_pins $name/[[$a getMTerm] getName]] -to [get_pins $name/[[$o getMTerm] getName]] -max
 puts "ENDPAD $name"
}
