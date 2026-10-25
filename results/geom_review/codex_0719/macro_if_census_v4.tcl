# macro_if_census.tcl -- S81-CORES3/PH 2026-10-25: F6 macro-interface census on a post-CTS/GRT odb (read-only).
# env: ODB, OT_CORNER (TT|FF), OUT (json path). Kit mounted at /work (constraint.sdc, macros/*_<c>.lib, config.mk vclk).
# Per macro signal pin: edge (W/E/N/S of the macro bbox), the registers in its 1-level timing cone (fan-in for macro
# inputs, fan-out for macro outputs), Manhattan distance pin->reg, reg CK arrival vs macro clk-pin arrival,
# worst setup / hold slack through the pin.
set C $::env(OT_CORNER); set c [string tolower $C]
set fh [open /work/config.mk]
foreach ln [split [read $fh] "\n"] {
  if {[regexp {^export\s+(OT_VCLK_TT|OT_VCLK_FF|LAYER_PARASITICS_FILE)\s*\??=\s*(\S+)} $ln -> k v]} { set ::env($k) $v }
}
close $fh
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(ODB)
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_sdc /work/constraint.sdc
set bound [expr {$C eq "FF" ? $::env(OT_VCLK_FF) : $::env(OT_VCLK_TT)}]
set vck [lsearch -all -inline -not [all_clocks] [get_clocks clk]]
if {[llength $vck] == 1} { set_clock_latency -source $bound $vck }
source $::env(LAYER_PARASITICS_FILE)
set mode placement
if {[catch {estimate_parasitics -global_routing}]} { estimate_parasitics -placement } else { set mode global_routing }
set_propagated_clock [get_clocks clk]
set per [get_property [get_clocks clk] period]
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ::if_db [dict create]
foreach ii [$blk getInsts] { set nn [regsub -all {\\} [$ii getName] {}]; dict set ::if_db $nn $ii }
proc ck_arr {pin} {
  global per
  if {[catch {set a [get_property $pin arrival_max_rise]}]} { return "" }
  if {![string is double -strict $a]} { return "" }
  return $a
}
set out [open $::env(OUT) w]
puts $out "{\"corner\": \"$C\", \"parasitics\": \"$mode\", \"bound_ps\": $bound, \"macros\": \["
set firstm 1
foreach inst [$blk getInsts] {
  set m [$inst getMaster]
  if {![$m isBlock]} continue
  set bb [$inst getBBox]
  set mx0 [expr {[$bb xMin]/double($dbu)}]; set my0 [expr {[$bb yMin]/double($dbu)}]
  set mx1 [expr {[$bb xMax]/double($dbu)}]; set my1 [expr {[$bb yMax]/double($dbu)}]
  set iname [$inst getName]
  set ckarr ""
  set rows {}
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] ni {SIGNAL CLOCK}} continue
    set net [$it getNet]
    if {$net eq "NULL"} continue
    set pn "$iname/[$mt getName]"
    set p [get_pins -quiet $pn]
    if {$p eq ""} continue
    set ib [$it getBBox]
    set px [expr {([$ib xMin]+[$ib xMax])/2.0/$dbu}]; set py [expr {([$ib yMin]+[$ib yMax])/2.0/$dbu}]
    set dw [expr {abs($px-$mx0)}]; set de [expr {abs($mx1-$px)}]; set ds [expr {abs($py-$my0)}]; set dn [expr {abs($my1-$py)}]
    set edge W; set dmin $dw
    foreach {e d} [list E $de S $ds N $dn] { if {$d < $dmin} { set edge $e; set dmin $d } }
    if {[get_property $p is_clock]} { set ckarr [ck_arr $p]; continue }
    set dir [get_property $p direction]
    # tie-driven inputs: skip (constant)
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv [[[$t getInst] getMaster] getName] } }
    if {[string match "TIE*" $drv]} continue
    if {$dir eq "input"} {
      set regs [get_fanin -to $p -flat -startpoints_only -trace_arcs all]
    } else {
      set regs [get_fanout -from $p -flat -endpoints_only -trace_arcs all]
    }
    set best 1e9; set rn ""; set ra ""
    foreach r $regs {
      set rinst [regsub {/[^/]+$} [get_full_name $r] {}]
      set rinst [regsub -all {\\} $rinst {}]
      set di "NULL"
      if {[dict exists $::if_db $rinst]} {set di [dict get $::if_db $rinst]}
      if {$di eq "NULL"} continue
      if {[[$di getMaster] isBlock]} continue
      set loc [$di getLocation]
      set d [expr {abs([lindex $loc 0]/double($dbu)-$px)+abs([lindex $loc 1]/double($dbu)-$py)}]
      if {$d < $best} { set best $d; set rn $rinst }
    }
    if {$rn ne ""} {
      set ckp [get_pins -quiet $rn/CLK]
      if {$ckp ne ""} { set ra [ck_arr $ckp] }
    }
    set ss ""; set hs ""
    catch {set ss [get_property $p slack_max]}
    catch {set hs [get_property $p slack_min]}
    lappend rows [list [$mt getName] $dir $edge $best $rn $ra $ss $hs]
  }
  if {!$firstm} { puts $out "," }
  set firstm 0
  puts $out "{\"inst\": \"$iname\", \"master\": \"[$m getName]\", \"bbox\": \[$mx0, $my0, $mx1, $my1\], \"clk_arrival\": \"$ckarr\", \"pins\": \["
  set f 1
  foreach r $rows {
    lassign $r n d e b rn ra ss hs
    if {!$f} { puts $out "," }
    set f 0
    puts -nonewline $out "\[\"$n\", \"$d\", \"$e\", [format %.2f $b], \"$rn\", \"$ra\", \"$ss\", \"$hs\"\]"
  }
  puts $out "\]}"
}
puts $out "\], \"setup_wns_ps\": [expr {[sta::worst_slack_cmd max]*1e12}], \"hold_wns_ps\": [expr {[sta::worst_slack_cmd min]*1e12}]}"
close $out
# worst hold / setup paths, for classification
report_checks -path_delay min -group_path_count 20 -format end > [file rootname $::env(OUT)]_hold_end.rpt
report_checks -path_delay max -group_path_count 20 -format end > [file rootname $::env(OUT)]_setup_end.rpt
report_checks -path_delay min -group_path_count 3 -fields {input_pin} -format full_clock_expanded > [file rootname $::env(OUT)]_hold3.rpt
puts "CENSUS done $C $mode"
