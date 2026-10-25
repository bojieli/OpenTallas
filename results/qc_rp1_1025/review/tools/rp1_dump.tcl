# QC-RP1 geometry/clock dump (placement RC) of a placed or CTS DB: ODB, OT_CORNER tt|ff, OUT
set C [string toupper $::env(OT_CORNER)]; set c [string tolower $C]
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_$c.lib
read_db $::env(ODB)
read_sdc /work/constraint.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set cts [expr {[llength [get_cells -quiet clkbuf*]] > 0 || [llength [get_cells -quiet *cqb*]] > 0}]
if {$cts} { set_propagated_clock [all_clocks] }
set f [open $::env(OUT) w]
set blk [ord::get_db_block]; set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.2f [expr {$v / double($::dbu)}]] }
set die [$blk getDieArea]
puts $f "DIE\t[um [$die xMin]]\t[um [$die yMin]]\t[um [$die xMax]]\t[um [$die yMax]]"
foreach i [$blk getInsts] {
  set m [$i getMaster]; set mn [$m getName]
  if {[string match "FILL*" $mn] || [string match "DECAP*" $mn] || [string match "TAPCELL*" $mn]} continue
  set bb [$i getBBox]; set kind std; if {[$m isBlock]} { set kind macro }
  if {$kind eq "std" && ![string match "*DFF*" $mn] && ![string match "*BUF*" $mn] && ![string match "*INV*" $mn]} continue
  puts $f "INST\t[$i getName]\t$mn\t$kind\t[um [$bb xMin]]\t[um [$bb yMin]]\t[um [$bb xMax]]\t[um [$bb yMax]]"
}
foreach n [$blk getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  set drv ""; set sinks {}
  foreach it [$n getITerms] { if {[$it isOutputSignal]} { set drv [[$it getInst] getName] } else { lappend sinks "[[$it getInst] getName]/[[$it getMTerm] getName]" } }
  foreach bt [$n getBTerms] { if {$drv eq ""} { set drv "PORT:[$bt getName]" } }
  puts $f "CNET\t[$n getName]\t$drv\t[llength $sinks]\t[join $sinks { }]"
}
foreach p [all_registers -clock_pins] { set a ""; catch {set a [get_property $p arrival_max_rise]}; puts $f "CK\t[get_full_name $p]\t$a" }
set regs {}
foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] 1 }
foreach p [get_fanout -from [all_inputs -no_clocks] -flat -endpoints_only -trace_arcs all] {
  set i [regsub {/[^/]+$} [get_full_name $p] {}]; if {[dict exists $regs $i]} { puts $f "PINREG\tin\t$i" } }
foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
  set i [regsub {/[^/]+$} [get_full_name $p] {}]; if {[dict exists $regs $i]} { puts $f "PINREG\tout\t$i" } }
if {$cts} {
  foreach pa [find_timing_paths -path_delay min -group_path_count 300 -endpoint_path_count 1 -slack_max 0] {
    puts $f "HOLD\t[get_full_name [get_property $pa endpoint]]\t[get_full_name [get_property $pa startpoint]]\t[get_property $pa slack]" }
  puts $f "WNS\t[sta::time_sta_ui [sta::worst_slack_cmd min]]\t[sta::endpoint_violation_count min]\t[sta::time_sta_ui [sta::worst_slack_cmd max]]"
}
close $f
puts DUMP_DONE
