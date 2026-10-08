# CLAUDE setup-triage 2026-10-07: CONSISTENT die-link IO budget (owner-delegated decision, coordinator 2026-10-07).
#
# A registered die link is  sender flop -> sender pin -> die wire / pin station -> receiver pin -> receiver flop.  Its
# setup equation, with the two blocks' clock arrivals differing by up to SKEW, is
#     S (sender clk->Q + reg->pin) + LINK (measured wire + station) + R (receiver pin->flop + setup) + SKEW <= T - 60
# so the two SDCs of one link must split ONE budget:  S + R = T - 60 - SKEW - LINK.  The per-block generators in use
# (0.2T-outside, W2 make_sdc.py, budget sheets) give each side the remainder after assuming the OTHER side small, so the
# two windows overlap (W2: 338 + 263 = 601 ps vs 423 available at WIRE 200).  This SDC re-applies every data port's
# max delay from the consistent split, referenced to a virtual clock at the block's MEASURED mid insertion:
#     input  max = T - 60 - R      output max = T - 60 - S      (uncertainty 60 is applied by STA itself)
# Knobs (Tcl vars before sourcing, else env, else default): ot_lb_skew (150, inter-region; 90 intra), ot_lb_link
# (114 = 100 um pin-station segment x 1.135 ps/um SS), ot_lb_sfrac (0.5).  SETUP ONLY: read it in the SS session;
# hold keeps flow-hold's rule-H1 SDC (this file sets no -min).  Exceptions (false/multicycle paths from/to ports) stay.
proc ot_lb_get {n d} { if {[info exists ::$n]} { return [set ::$n] }; if {[info exists ::env($n)]} { return $::env($n) }; return $d }
set ot_lb_skew [ot_lb_get ot_lb_skew 150]
set ot_lb_link [ot_lb_get ot_lb_link 114]
set ot_lb_sfrac [ot_lb_get ot_lb_sfrac 0.5]
set ot_lb_clks {}
foreach c [all_clocks] {
  set src [get_property $c sources]
  if {[llength $src] == 1 && [get_property $c is_generated] == 0 && [llength [get_ports -quiet [get_full_name [lindex $src 0]]]]} { lappend ot_lb_clks $c }
}
if {[llength $ot_lb_clks] < 1} { error "OT_LINK_BUDGET: no port-sourced clock" }
# one virtual clock per port-sourced clock, at that clock's measured mid insertion
set ot_lb_vmap [dict create]
foreach c $ot_lb_clks {
  set cn [get_full_name $c]
  set T [get_property $c period]
  sta::redirect_string_begin
  report_clock_latency -clock $c
  set rs [sta::redirect_string_end]
  if {![regexp {rise -> rise.*?([0-9.]+)\s+([0-9.]+)\s+latency} $rs -> lo hi]} { puts "OT_LINK_BUDGET no latency for $cn (no sinks?)"; continue }
  set L [expr {($lo + $hi) / 2.0}]
  set B [expr {$T - 60.0 - $ot_lb_skew - $ot_lb_link}]
  set S [expr {$ot_lb_sfrac * $B}]; set R [expr {$B - $S}]
  create_clock -name ot_lb_v_$cn -period $T
  set_clock_latency $L [get_clocks ot_lb_v_$cn]
  set_clock_uncertainty -setup 60 [get_clocks ot_lb_v_$cn]
  dict set ot_lb_vmap $cn [list ot_lb_v_$cn [expr {$T - 60.0 - $R}] [expr {$T - 60.0 - $S}]]
  puts [format "OT_LINK_BUDGET clock %s T %.3f L %.1f (%.1f..%.1f) skew %s link %s -> S %.1f R %.1f; in max %.1f out max %.1f" $cn $T $L $lo $hi $ot_lb_skew $ot_lb_link $S $R [expr {$T - 60.0 - $R}] [expr {$T - 60.0 - $S}]]
}
if {[dict size $ot_lb_vmap] == 0} { error "OT_LINK_BUDGET: no measured clock" }
set ot_lb_default [lindex [dict keys $ot_lb_vmap] 0]
# the port-sourced clock of the first register reached from a port through combinational cells (odb walk; a
# generated clock maps to its master's port clock)
proc ot_lb_clk_of_inst {inst} {
  foreach cp {CLK clk CK} {
    set ck [get_pins -quiet "[string map {/ .} [$inst getName]]/$cp"]
    if {[llength $ck] == 0} { set ck [get_pins -quiet "[$inst getName]/$cp"] }
    if {[llength $ck] == 0} continue
    foreach c [get_property $ck clocks] {
      set n [get_full_name $c]
      for {set i 0} {$i < 8 && [get_property [get_clocks $n] is_generated]} {incr i} { set n [get_full_name [get_property [get_clocks $n] master_clock]] }
      if {[dict exists $::ot_lb_vmap $n]} { return $n }
    }
  }
  return ""
}
proc ot_lb_is_seq {inst} { return [regexp {^(DFF|DHL|DLL|SDF|ASYNC|ICG)} [[$inst getMaster] getName]] }
proc ot_lb_domain {portname dir} {
  set bt [[ord::get_db_block] findBTerm $portname]
  if {$bt eq "NULL" || $bt eq ""} { return "" }
  set nets [list [$bt getNet]]; set seen [dict create]; set k 0
  while {[llength $nets] && $k < 4000} {
    set n [lindex $nets 0]; set nets [lrange $nets 1 end]; incr k
    if {$n eq "NULL" || [dict exists $seen [$n getName]]} continue
    dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      set inst [$it getInst]
      if {$dir eq "in" && ![$it isInputSignal]} continue
      if {$dir eq "out" && ![$it isOutputSignal]} continue
      if {[ot_lb_is_seq $inst]} { set d [ot_lb_clk_of_inst $inst]; if {$d ne ""} { return $d }; continue }
      foreach it2 [$inst getITerms] {
        if {$dir eq "in" && [$it2 isOutputSignal]} { lappend nets [$it2 getNet] }
        if {$dir eq "out" && [$it2 isInputSignal]} { set nn [$it2 getNet]; if {$nn ne "NULL" && [$nn getSigType] ni {POWER GROUND CLOCK}} { lappend nets $nn } }
      }
    }
  }
  return ""
}
set ot_lb_gsrc {}
foreach c [all_clocks] { foreach s [get_property $c sources] { lappend ot_lb_gsrc [get_full_name $s] } }
set ot_lb_in [all_inputs -no_clocks]
set ot_lb_out {}
foreach p [all_outputs] { if {[lsearch -exact $ot_lb_gsrc [get_full_name $p]] < 0} { lappend ot_lb_out $p } }
unset_input_delay $ot_lb_in
unset_output_delay $ot_lb_out
set ot_lb_multi [expr {[dict size $ot_lb_vmap] > 1}]
set ot_lb_n [dict create]
foreach p $ot_lb_in {
  set d $ot_lb_default
  if {$ot_lb_multi} { set x [ot_lb_domain [get_full_name $p] in]; if {$x ne ""} { set d $x } }
  lassign [dict get $ot_lb_vmap $d] vc imax omax
  set_input_delay -max $imax -clock $vc $p
  dict incr ot_lb_n "in:$d"
}
foreach p $ot_lb_out {
  set d $ot_lb_default
  if {$ot_lb_multi} { set x [ot_lb_domain [get_full_name $p] out]; if {$x ne ""} { set d $x } }
  lassign [dict get $ot_lb_vmap $d] vc imax omax
  set_output_delay -max $omax -clock $vc $p
  dict incr ot_lb_n "out:$d"
}
puts "OT_LINK_BUDGET ports $ot_lb_n"
