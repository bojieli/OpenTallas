# QC-S8BP independent single-corner GRT measurement of a 5_1_grt ODB: related-pair skew (CPPR, pair_skew.tcl),
# boundary pin-register clock insertion I, per-sink clock arrival, clock tree geometry, worst hold/setup paths.
# env: OT_CORNER tt|ff, SRC (kit dir, read-only), NICK (design nickname), SRAM (macro lib basename), OUT (dir)
set C [string toupper $::env(OT_CORNER)]; set c [string tolower $C]
set S $::env(SRC); set B $S/run/results/asap7/$::env(NICK)/base; set O $::env(OUT)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
read_liberty $S/macros/$::env(SRAM)_$c.lib
read_db $B/5_1_grt.odb
read_sdc $B/5_1_grt.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment * 0.0
set_macro_extension 2
global_route -congestion_iterations 30
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
foreach k [all_clocks] { if {[llength [get_property $k sources]]} { set_clock_latency -source 0 $k } }
set ::env(CORNER) ${C}_GRT
set ::env(OT_PS_OUT) $O/pair_$c.tsv
source $S/pair_skew.tcl
# restore signoff uncertainties (pair_skew zeroes them)
set_clock_uncertainty 60 -setup [all_clocks]
set_clock_uncertainty 25 -hold [all_clocks]
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup 30
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup 30
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold 12.5
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -hold 12.5
set f [open $O/dump_$c.tsv w]
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.2f [expr {$v / double($::dbu)}]] }
set die [$blk getDieArea]
puts $f "DIE\t[um [$die xMin]]\t[um [$die yMin]]\t[um [$die xMax]]\t[um [$die yMax]]"
foreach bt [$blk getBTerms] {
  set bb [$bt getBBox]
  puts $f "PORT\t[$bt getName]\t[um [expr {([$bb xMin]+[$bb xMax])/2}]]\t[um [expr {([$bb yMin]+[$bb yMax])/2}]]\t[$bt getIoType]"
}
foreach i [$blk getInsts] {
  set m [$i getMaster]; set mn [$m getName]
  if {[string match "FILL*" $mn] || [string match "DECAP*" $mn] || [string match "TAPCELL*" $mn]} continue
  set bb [$i getBBox]; set kind std
  if {[$m isBlock]} { set kind macro }
  puts $f "INST\t[$i getName]\t$mn\t$kind\t[um [$bb xMin]]\t[um [$bb yMin]]\t[um [$bb xMax]]\t[um [$bb yMax]]"
}
foreach n [$blk getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  set drv ""; set sinks {}
  foreach it [$n getITerms] { if {[$it isOutputSignal]} { set drv [[$it getInst] getName] } else { lappend sinks "[[$it getInst] getName]/[[$it getMTerm] getName]" } }
  foreach bt [$n getBTerms] { if {$drv eq ""} { set drv "PORT:[$bt getName]" } }
  puts $f "CNET\t[$n getName]\t$drv\t[llength $sinks]\t[join $sinks { }]"
}
foreach p [all_registers -clock_pins] {
  set a ""; catch {set a [get_property $p arrival_max_rise]}
  puts $f "CK\t[get_full_name $p]\t$a"
}
set regs {}
foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] 1 }
set asy {}; foreach p [all_registers -async_pins] { dict set asy [get_full_name $p] 1 }
foreach p [get_fanout -from [all_inputs -no_clocks] -flat -endpoints_only -trace_arcs all] {
  set n [get_full_name $p]; if {[dict exists $asy $n]} continue
  set i [regsub {/[^/]+$} $n {}]; if {[dict exists $regs $i]} { puts $f "PINREG\tin\t$i" }
}
foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
  set i [regsub {/[^/]+$} [get_full_name $p] {}]; if {[dict exists $regs $i]} { puts $f "PINREG\tout\t$i" }
}
foreach dl {min max} tag {HOLD SETUP} {
  foreach pa [find_timing_paths -path_delay $dl -group_path_count 2000 -endpoint_path_count 1 -slack_max 0] {
    puts $f "$tag\t[get_full_name [get_property $pa endpoint]]\t[get_full_name [get_property $pa startpoint]]\t[get_property $pa slack]"
  }
}
report_worst_slack -min -digits 2
report_worst_slack -max -digits 2
report_tns -digits 2
close $f
puts MEAS_DONE
exit
