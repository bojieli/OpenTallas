# NEARMISS-STRUCT geometry/clock/violator dump, appended after the signoff session's STD overlay (same libs/SDC/overlay as signoff)
set f [open /nm/dump_[string tolower @C@].tsv w]
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
foreach n [$blk getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  set drv ""; set sinks {}
  foreach it [$n getITerms] { if {[$it isOutputSignal]} { set drv [[$it getInst] getName] } else { lappend sinks "[[$it getInst] getName]/[[$it getMTerm] getName]" } }
  foreach bt [$n getBTerms] { if {$drv eq ""} { set drv "PORT:[$bt getName]" } }
  puts $f "CNET\t[$n getName]\t$drv\t[llength $sinks]\t[join $sinks { }]"
}
foreach {tag dly} {HOLD min SETUP max} {
  foreach pa [find_timing_paths -path_delay $dly -group_path_count 1000 -endpoint_path_count 1 -slack_max 0] {
    set sp [get_full_name [get_property $pa startpoint]]; set ep [get_full_name [get_property $pa endpoint]]
    set npts ""; catch {set npts [llength [get_property $pa points]]}
    puts $f "$tag\t$ep\t$sp\t[get_property $pa slack]\t\t\t[get_full_name [get_property $pa endpoint_clock]]\t$npts"
  }
}
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
foreach p [all_registers -clock_pins] {
  set a ""; catch {set a [get_property $p arrival_max_rise]}
  puts $f "CK\t[get_full_name $p]\t$a"
}
set regs {}
foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] 1 }
foreach p [all_inputs -no_clocks] {
  foreach q [get_fanout -from $p -flat -endpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $q] {}]; if {[dict exists $regs $i]} { puts $f "P2R\tin\t[get_full_name $p]\t$i" }
  }
}
foreach p [all_outputs] {
  foreach q [get_fanin -to $p -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $q] {}]; if {[dict exists $regs $i]} { puts $f "P2R\tout\t[get_full_name $p]\t$i" }
  }
}
# macro interface registers
foreach i [$blk getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set iname [$i getName]
  foreach it [$i getITerms] {
    set n [$it getNet]; if {$n eq "NULL"} continue
    if {[$n getSigType] ne "SIGNAL"} continue
    set pn "$iname/[[$it getMTerm] getName]"
    set sp [get_pins -quiet $pn]; if {![llength $sp]} continue
    if {[$it isInputSignal]} {
      foreach q [get_fanin -to $sp -flat -startpoints_only -trace_arcs all] { set r [regsub {/[^/]+$} [get_full_name $q] {}]; if {[dict exists $regs $r] && $r ne $iname} { puts $f "MIF\tin\t$pn\t$r" } }
    } elseif {[$it isOutputSignal]} {
      foreach q [get_fanout -from $sp -flat -endpoints_only -trace_arcs all] { set r [regsub {/[^/]+$} [get_full_name $q] {}]; if {[dict exists $regs $r] && $r ne $iname} { puts $f "MIF\tout\t$pn\t$r" } }
    }
  }
}
close $f
puts NM_DUMP_DONE
exit
