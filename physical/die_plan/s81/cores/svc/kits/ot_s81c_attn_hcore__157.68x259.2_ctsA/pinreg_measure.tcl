# pinreg_measure.tcl -- FLOW-CANARY 2026-10-25: ONE definition of the boundary pin-register clock quantity, shared by
# the pre-route insertion gate (postcts_gate.tcl) and the GRT pre-pass pin-register pad (pinreg_pad.tcl), so the pad
# balances exactly what the gate checks.  The routing context is tapbal_grt.tcl's job (same GRT options as ORFS
# global_route.tcl, incl. -resistance_aware: without it the s81 slice_station__t12 canary pre-pass read the pin-register
# mean 245.94 ps vs 226.32 with it, and the gate on 5_1_grt.odb read 226.54; FLOW-CANARY diag 10-25).
# Set: registers in the fanout of the data inputs / fanin of the outputs (the sign-off clock check's pin registers).
# Measure: clock_family.tcl ot_cf_wire (active-edge propagated clock arrival); fallback arrival_max_rise folded to
# the active edge when clock_family is absent.  Callers set propagated clocks + parasitics before measuring.
#   ot_pinreg_set        -> dict {instance name -> CK pin}, sorted by instance name
#   ot_pinreg_arr p clk  -> arrival (ps) of CK pin p for clock clk, or "" when not timed
proc ot_pinreg_set {} {
  set regs {}
  foreach p [all_registers -clock_pins] { dict set regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
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
proc ot_pinreg_arr {p clk} {
  set a ""
  if {[llength [info commands ot_cf_wire]]} { catch {set a [ot_cf_wire $p $clk]} }
  if {$a eq ""} {
    set per [get_property $clk period]
    if {[catch {set a [get_property $p arrival_max_rise]}]} { return "" }
    if {[string is double -strict $a] && $a >= $per / 2.0 && $a < $per} { set a [expr {$a - $per / 2.0}] }
  }
  if {![string is double -strict $a]} { return "" }
  return $a
}
