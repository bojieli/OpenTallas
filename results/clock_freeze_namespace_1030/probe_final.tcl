foreach l $::env(OT_LIBS) {read_liberty $l}
read_db /work/run/results/asap7/hc_kv3_pv_pair__380_16x190_08_fMX/base/5_1_grt.odb
read_sdc /work/constraint.sdc
source /work/clk_freeze.tcl
set reference [ot_clk_dbnets]
set wanted {};foreach n $reference {lappend wanted [$n getName]};set wanted [lsort $wanted]
namespace eval ::ot_mm_fixed [list source /out/clk_freeze_fixed.tcl]
rename ::sta::find_all_clk_nets ::sta::saved_find_for_census
set ::calls 0;set ::testmode normal
proc ::sta::find_all_clk_nets {} {
  incr ::calls
  if {$::testmode eq "error"} {error "injected unavailable clock census"}
  if {$::testmode eq "empty"} {return {}}
  return [::sta::saved_find_for_census]
}
set fixed [::ot_mm_fixed::ot_clk_dbnets]
set names {};foreach n $fixed {lappend names [$n getName]};set names [lsort $names]
if {$names ne $wanted || [llength $fixed]!=1542 || $::calls!=1} {error "actual global STA enumeration not used or incomplete"}
puts "PV_FINAL_CENSUS PASS exact1542netnames global_calls$::calls public_clocks[llength [::all_clocks]] actual_seq_clockpins[llength [::all_registers -clock_pins]] relative_lookup[namespace eval ::ot_mm_fixed {llength [info commands sta::find_all_clk_nets]}]"
foreach mode {error empty} {
  set ::testmode $mode
  if {![catch {::ot_mm_fixed::ot_clk_dbnets} msg]} {error "actual native zero/error census escaped failclosed guard"}
  puts "PV_FINAL_NEGATIVE $mode CAUGHT $msg"
}
rename ::sta::find_all_clk_nets {}
rename ::sta::saved_find_for_census ::sta::find_all_clk_nets
puts "PV_FINAL_READONLY nofreeze/route/write_db; input posthook DB has positiveCLOCKcache so originalnative0NETS causalclaim unproven"
exit
