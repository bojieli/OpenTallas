# worst setup (TT) / hold (FF) slack per launch child -> capture child of the composition; env CORNER, DB, SDC
set C $::env(CORNER); set c [string tolower $C]
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $PLAT/lib/NLDM/*RVT_${C}*] { read_liberty $l }
foreach v {physical/s81_ph_views/closed/dsfd_engram_lkp/dsfd_engram_lkp physical/s81_ph_views/closed/dsfd_engram_sink/dsfd_engram_sink physical/s81_engc_tiles/views/ot_engc_t_win/ot_engc_t_win physical/s81_engc_tiles/views/ot_engc_t_io/ot_engc_t_io physical/s81_engc_tiles/views/ot_engc_t_ws/ot_engc_t_ws physical/s81_engc_tiles/views/ot_engc_t_pbb/ot_engc_t_pbb physical/s81_engc_tiles/views/ot_engc_t_pbc/ot_engc_t_pbc} { read_liberty /src/${v}_$c.lib }
read_db /base/$::env(DB)
read_sdc /base/$::env(SDC)
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef /base/$::env(SPEF) } else { source $PLAT/setRC.tcl; estimate_parasitics -placement }
set_propagated_clock [get_clocks core_clk]
set kind $::env(PATH_DELAY)
# Owner fixed same-level/cross-level setup150/210; H1 hold100.
# Use210 conservatively for all core paths, then retain pair-specific raw checks separately.
if {$::env(STRICT_BUDGET) ne "raw"} {
  set_clock_uncertainty -setup $::env(STRICT_BUDGET) [all_clocks]
  set_clock_uncertainty -hold 100 [all_clocks]
}
set ends {u_win u_io u_ws u_sink u_lkp u_pb0 u_pb1 u_pb2}
proc ot_w {from to kind} {
  set ps [find_timing_paths -path_delay $kind -from $from -to $to -group_path_count 1 -sort_by_slack]
  if {![llength $ps]} { return "" }
  return [format %.1f [get_property [lindex $ps 0] slack]]
}
foreach a $ends {
  set fa [get_pins -filter "direction==output" $a/*]
  foreach bq $ends {
    if {$a eq $bq} continue
    set s [ot_w $fa [get_pins -filter "direction==input" $bq/*] $kind]
    if {$s ne ""} { puts "PAIR $C $kind $a $bq $s" }
  }
  set s [ot_w $fa [all_outputs] $kind]; if {$s ne ""} { puts "PAIR $C $kind $a OUT $s" }
  set s [ot_w [all_inputs -no_clocks] [get_pins -filter "direction==input" $a/*] $kind]; if {$s ne ""} { puts "PAIR $C $kind IN $a $s" }
}
# Dedicated local reset checks: stage-to-stage and conditioner output to
# hardened child reset are measured without multicycle or false-path waivers.
foreach child {win io ws pb1 pb0 pb2 lkp sink} {
  set regs [get_cells -quiet *u_rst_${child}*]
  if {![llength $regs]} { error "ENGC reset cells missing: $child" }
  # Only sequential QN/D pins form the conditioner stage chain. Synthesis
  # also names reset input inverters under u_rst_<child>; including their Y
  # pins mislabeled external recovery as a stage-to-stage data path.
  set q {}; set d {}; set async_controls {}
  foreach pin [get_pins -of_objects $regs] {
    set name [get_full_name $pin]
    if {[string match */QN $name]} { lappend q $pin }
    if {[string match */D $name]} { lappend d $pin }
    if {[string match */RESETN $name]} { lappend async_controls $pin }
  }
  if {[llength $q] != 2 || [llength $d] != 2 || [llength $async_controls] != 2} {
    error "ENGC reset stages not exactly two: $child Q=[llength $q] D=[llength $d] R=[llength $async_controls]"
  }
  set rpin rst
  if {$child in {lkp sink}} { set rpin rst_n }
  foreach pair [list [list STAGES $q $d] [list CHILD $q [get_pins u_${child}/$rpin]] [list ASYNC [get_ports {rst[0]}] $async_controls]] {
    lassign $pair tag from to
    set v [ot_w $from $to $kind]
    puts "RESET $C $kind $child $tag $v"
  }
}
puts "PAIR $C $kind WNS [format %.1f [sta::worst_slack -$kind]]"
set b [ord::get_db_block]
foreach child {win io ws pb1 pb0 pb2 lkp sink} {
  set macro [$b findInst u_$child]
  set expected [[$macro findITerm ck] getNet]
  set clocks 0
  foreach i [$b getInsts] {
    if {![string match *u_rst_${child}* [$i getName]]} continue
    foreach it [$i getITerms] {
      set mt [$it getMTerm]
      if {[$mt getSigType] ne "CLOCK" && [$mt getName] ni {CLK CK CP}} continue
      incr clocks
      if {[$it getNet] ne $expected} { error "RESET clock mismatch $child: [$i getName]" }
    }
  }
  if {$clocks != 2} { error "RESET $child clocks $clocks !=2" }
  puts "RESET_TOPOLOGY $C $child clocks=$clocks same_macro_net=1"
}
report_checks -path_delay $kind -group_path_count 5 -format full_clock_expanded -fields {slew cap fanout input net} -digits 3
exit
