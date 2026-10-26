set C $::env(C)
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_${C}_*.lib*]] {read_liberty $f}
read_db /work/run/results/asap7/kl_ot_dsrom_su_hcpost_lane_pr_v1b/base/4_cts.odb
read_sdc /work/constraint.sdc
if {$C eq "FF"} {set_clock_latency -source 202.5 [get_clocks vclk]}
set_propagated_clock [get_clocks clk]
set sta_recovery_removal_checks_enabled 1
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set B [ord::get_db_block]
set U [$B getDbUnitsPerMicron]
set fd [open /work/shift_clock_groups.tsv];set lines [split [read $fd] \n];close $fd
set expect [dict create]
foreach line [lrange $lines 1 end] {set z [split $line \t];if {[llength $z]<6} continue;set g [lindex $z 0];if {$g>=0} {dict lappend expect $g [lindex $z 1]}}
proc h_sinks {net} {
 set out {};set todo [list $net];set seen [dict create]
 while {[llength $todo]} {
  set n [lindex $todo end];set todo [lrange $todo 0 end-1]
  if {[dict exists $seen [$n getName]]} continue
  dict set seen [$n getName] 1
  foreach it [$n getITerms] {
   if {![$it isInputSignal]} continue
   set i [$it getInst];set m [[$i getMaster] getName]
   if {[regexp {^(BUF|INV|HB|CKINV|CKBUF)} $m]} {
    foreach o [$i getITerms] {if {[$o isOutputSignal] && [$o getNet] ne "NULL"} {lappend todo [$o getNet]}}
   } elseif {[regexp {DFF} $m] && [string match {*CLK*} [[$it getMTerm] getName]]} {lappend out [$i getName]}
  }
 }
 return [lsort -unique $out]
}
set fd [open /work/shift_actual_${C}.tsv w]
puts $fd "group\tname\tx_um\ty_um\tck_ps"
set ng 0;set nf 0;set maxspan 0
set fclock [dict create]
foreach p [all_registers -clock_pins] {set it [sta::sta_to_db_pin $p];if {$it ne "NULL"} {dict set fclock [[$it getInst] getName] $p}}
dict for {g names} $expect {
 set t [$B findInst hcpl_shift_tap_$g]
 if {$t eq "NULL"} {error "HCPL_SHIFT lost clocktap $g"}
 set got [h_sinks [[$t findITerm Y] getNet]]
 if {$got ne [lsort -unique $names]} {error "HCPL_SHIFT CTS changed group $g expected=[llength $names] got=[llength $got]"}
 set mn 1e9;set mx -1e9;set total 0
 foreach n $got {
  set p [dict get $fclock $n];set a [get_property $p arrival_max_rise]
  if {$a<$mn} {set mn $a};if {$a>$mx} {set mx $a};set total [expr {$total+$a}]
  set i [$B findInst $n];lassign [$i getLocation] x y
  puts $fd "$g\t$n\t[expr {$x/double($U)}]\t[expr {$y/double($U)}]\t$a"
 }
 set span [expr {$mx-$mn}];if {$span>$maxspan} {set maxspan $span}
 puts "HCPL_SHIFT ACTUAL $C group $g FF [llength $got] mean [expr {$total/[llength $got]}] min $mn max $mx span $span"
 incr ng;incr nf [llength $got]
}
close $fd
puts "HCPL_SHIFT OWNERSHIP_PASS $C groups $ng FF $nf maxspan $maxspan allFF [dict size $fclock]"
puts "HCPL_SHIFT TIMING $C setup [expr {[sta::worst_slack_cmd max]*1e12}] nsetup [sta::endpoint_violation_count max] hold [expr {[sta::worst_slack_cmd min]*1e12}] nhold [sta::endpoint_violation_count min]"
report_checks -path_delay min -group_path_count 10 -format full_clock_expanded > /work/shift_hold_${C}.rpt
report_checks -path_delay max -group_path_count 5 -format full_clock_expanded > /work/shift_setup_${C}.rpt

set shift_dp {}
foreach p [all_registers -data_pins] {
 set it [sta::sta_to_db_pin $p]
 if {$it eq "NULL"} continue
 if {[string first {u_core.u_d4.genblk1.g_line.line} [[$it getInst] getName]]>=0} {lappend shift_dp $p}
}
set pp [find_timing_paths -to $shift_dp -path_delay min -group_path_count 1]
if {[llength $pp]!=1} {error "HCPL_SHIFT no real delay-chain timing path"}
puts "HCPL_SHIFT DELAY_CHAIN_MIN $C slack_ps [get_property [lindex $pp 0] slack] data_pins [llength $shift_dp]"
report_checks -to $shift_dp -path_delay min -group_path_count 5 -format full_clock_expanded > /work/delay_chain_hold_${C}.rpt
