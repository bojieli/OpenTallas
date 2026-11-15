# pinreg_measure.tcl -- FLOW-CANARY 2026-10-25: ONE definition of the boundary pin-register clock quantity, shared by
# the pre-route insertion gate (postcts_gate.tcl) and the GRT pre-pass pin-register pad (pinreg_pad.tcl), so the pad
# balances exactly what the gate checks.  The routing context is tapbal_grt.tcl's job (same GRT options as ORFS
# global_route.tcl, incl. -resistance_aware: without it the s81 slice_station__t12 canary pre-pass read the pin-register
# mean 245.94 ps vs 226.32 with it, and the gate on 5_1_grt.odb read 226.54; FLOW-CANARY diag 10-25).
# Set: registers in the fanout of the data inputs / fanin of the outputs (the sign-off clock check's pin registers).
# Measure: clock_family.tcl ot_cf_wire (active-edge propagated clock arrival); fallback arrival_max_rise less the clock waveform
# offset (first rising edge) when clock_family is absent, never a magnitude test.  Callers set propagated clocks + parasitics before measuring.
#   ot_pinreg_set        -> clk-family boundary registers only, sorted by instance name
#   ot_pinreg_set_for_clock name -> same boundary census for another actual clock root
#   ot_pinreg_arr p clk  -> arrival (ps) of CK pin p for clock clk, or "" when not timed
proc ot_pinreg_set {} { return [ot_pinreg_set_for_clock clk] }
proc ot_pinreg_set_for_clock {name} {
  # Forwarded landing writers belong to their source clock, not the local clk
  # insertion budget. Use STA graph ownership, never instance-name exemptions.
  # Generated descendants of clk remain in its family. The edge-clock source
  # and landing-window timing retain their own SDC/sign-off obligations.
  set clock [get_clocks -quiet $name]
  if {[llength $clock] != 1} {error "OT_PINREG: missing unique clock $name"}
  if {[llength [info commands ot_cf_pins]]} {
    lassign [ot_cf_pins $clock] pins owners
  } else {
    set pins [all_registers -clock_pins -clock $clock]
  }
  set regs {}
  foreach p $pins { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
  set bnd {}
  set din [all_inputs -no_clocks]
  if {[llength $din]} {
    foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
      set i [regsub {/[^/]+$} [get_full_name $p] {}]
      if {[dict exists $regs $i]} { dict set bnd $i [dict get $regs $i] }
    }
  }
  if {[llength [all_outputs]]} {
    foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
      set i [regsub {/[^/]+$} [get_full_name $p] {}]
      if {[dict exists $regs $i]} { dict set bnd $i [dict get $regs $i] }
    }
  }
  set out {}
  foreach i [lsort [dict keys $bnd]] { dict set out $i [dict get $bnd $i] }
  return $out
}
# time of the clock's first rising edge (waveform offset, ps); 0 for the usual {0 T/2} waveform, T/2 for a {T/2 T} one
proc ot_pinreg_rise0 {clk} {
  set w 0.0
  if {![catch {set wf [$clk waveform]}] && [llength $wf] == 2 && ![catch {set w0 [sta::time_sta_ui [lindex $wf 0]]}] && [string is double -strict $w0]} { set w $w0 }
  return $w
}
proc ot_pinreg_arr {p clk} {
  set a ""
  if {[llength [info commands ot_cf_wire]]} { catch {set a [ot_cf_wire $p $clk]} }
  if {$a eq ""} {
    if {[catch {set a [get_property $p arrival_max_rise]}]} { return "" }
    # S81-TAPROWS 11-15 (FABLE-PD-S81C-0730 KIT-OPS-5): the arrival of a rising edge is measured from the clock's first rising
    # edge, whatever the insertion.  The old fold (a in [T/2, T) -> a - T/2) turned every register whose real insertion was
    # >= T/2 into a phantom early one (idxC 484.2 read 67.7, heA 504.3 read 87.8; one such register moved the reported min
    # from ~390-450 to 19-202 ps and fed the "200 ps face target").  Subtract the waveform offset only.
    if {[string is double -strict $a]} { set a [expr {$a - [ot_pinreg_rise0 $clk]}] }
  }
  if {![string is double -strict $a]} { return "" }
  return $a
}
