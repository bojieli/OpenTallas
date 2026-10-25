# QC-CQB geometry/clock dump of the routed vmr DB (RCX spef) for the GEOM review: one corner (OT_CORNER tt|ff)
set C [string toupper $::env(OT_CORNER)]; set c [string tolower $C]
set B /work/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
read_liberty /work/macros/ot_sram_1r1w_1024x256_m2_r2c2_$c.lib
read_db $B/6_final.odb
read_spef $B/6_final.spef
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
set f [open /work/geom/dump_$c.tsv w]
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
  set bb [$i getBBox]
  set kind std
  if {[$m isBlock]} { set kind macro }
  puts $f "INST\t[$i getName]\t$mn\t$kind\t[um [$bb xMin]]\t[um [$bb yMin]]\t[um [$bb xMax]]\t[um [$bb yMax]]"
}
# clock nets: driver -> sinks (tree edges)
foreach n [$blk getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  set drv ""; set sinks {}
  foreach it [$n getITerms] { if {[$it isOutputSignal]} { set drv [[$it getInst] getName] } else { lappend sinks "[[$it getInst] getName]/[[$it getMTerm] getName]" } }
  foreach bt [$n getBTerms] { if {$drv eq ""} { set drv "PORT:[$bt getName]" } }
  puts $f "CNET\t[$n getName]\t$drv\t[llength $sinks]\t[join $sinks { }]"
}
# clock arrivals at every register / macro clock pin (source latency 0 basis)
foreach p [all_registers -clock_pins] {
  set a ""; catch {set a [get_property $p arrival_max_rise]}
  puts $f "CK\t[get_full_name $p]\t$a"
}
# pin registers (boundary traversal like signoff.py)
set regs {}
foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] 1 }
foreach p [get_fanout -from [all_inputs -no_clocks] -flat -endpoints_only -trace_arcs all] {
  set i [regsub {/[^/]+$} [get_full_name $p] {}]; if {[dict exists $regs $i]} { puts $f "PINREG\tin\t$i" }
}
foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
  set i [regsub {/[^/]+$} [get_full_name $p] {}]; if {[dict exists $regs $i]} { puts $f "PINREG\tout\t$i" }
}
# hold violators (std boundary overlay as signoff)
foreach pa [find_timing_paths -path_delay min -group_path_count 400 -endpoint_path_count 1 -slack_max 0] {
  set sp [get_full_name [get_property $pa startpoint]]; set ep [get_full_name [get_property $pa endpoint]]
  puts $f "HOLD\t$ep\t$sp\t[get_property $pa slack]\t[get_property $pa arrival]\t[get_property $pa required]\t[get_full_name [get_property $pa endpoint_clock]]"
}
close $f
puts DUMP_DONE
