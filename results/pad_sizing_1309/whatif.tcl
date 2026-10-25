set corner $::env(CORNER)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${corner}_nldm_*.lib*] {read_liberty $f}
read_db /head/run/results/asap7/dp_hd_turn_a/base/6_final.odb
read_sdc /head/run/results/asap7/dp_hd_turn_a/base/6_final.sdc
read_spef /head/run/results/asap7/dp_hd_turn_a/base/6_final.spef
set_propagated_clock [get_clocks clk]
source /out/canonical_clock_family.tcl
set blk [ord::get_db_block]
set pads {};set netpad {};set groups {}
foreach i [$blk getInsts] {
 set name [$i getName]
 if {![string match ot_prp_d* $name]} continue
 lappend pads $name
 foreach it [$i getITerms] {if {[$it isOutputSignal]} {dict set netpad [[$it getNet] getName] $name}}
}
foreach p [all_registers -clock_pins] {
 set it [sta::sta_to_db_pin $p]
 if {$it eq "NULL" || [$it getNet] eq "NULL"} continue
 set nn [[$it getNet] getName]
 if {[dict exists $netpad $nn]} {dict lappend groups [dict get $netpad $nn] $p}
}
if {[llength $pads]!=35 || [dict size $groups]!=35} {error "Missing expected35 existing pad groups"}
set fp [open /out/whatif_${corner}.tsv w]
puts $fp "cell\tpad\tsinks\tmean_clock_ps\tmin_clock_ps\tmax_clock_ps"
foreach cell {BUFx2_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx12f_ASAP7_75t_R} {
 foreach pad $pads {replace_cell $pad $cell}
 # Re-read identical extracted wire networks after the sizing update. Cell pin
 # capacitances come from the replacement Liberty; positions/wires are frozen.
 read_spef /head/run/results/asap7/dp_hd_turn_a/base/6_final.spef
 set_propagated_clock [get_clocks clk]
 sta::worst_slack_cmd max
 ot_cf_refresh
 dict for {pad pins} $groups {
  set vals {}
  foreach pin $pins {lappend vals [ot_cf_wire $pin [get_clocks clk]]}
  set sorted [lsort -real $vals]
  set avg [expr {[tcl::mathop::+ {*}$vals]/[llength $vals]}]
  puts $fp "$cell\t$pad\t[llength $vals]\t$avg\t[lindex $sorted 0]\t[lindex $sorted end]"
 }
 puts "WHATIF $corner $cell groups [dict size $groups]"
}
close $fp
