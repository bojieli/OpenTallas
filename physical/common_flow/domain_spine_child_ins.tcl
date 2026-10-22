# domain_spine_child_ins.tcl (SQ-TTC4 2026-10-21, Q.STA.TTC.4): CLOCK LATENCY ACROSS THE HIERARCHY for the per-domain
# spatial spine (tools/ref_tile/domain_spatial_spine.py, spec domain_spatial_spine.child_insertion "boundary_record").
#
# Why: a landed cluster root is judged at the CHILD FLOPS (landed-regions standard; pre_route_gate.root_child_flops:
# hard-child clock-pin arrival + the child's closed-record insertion vs the root's soft flops, TT and FF <= 80 ps).
# The canonical engine (clock_spine.tcl, unchanged) already TAPS a leaf with its own insertion early in the symmetric
# builder (::ot_sp_child_ins), but its leaf-arrival measure balances the PIN.  safe12c LRT fixture: ck_core leaves
# 25.0 ps, yet hard child u_gi.g_wtn.u_wtn (R 141.6) lands its flops 149.2 ps after the soft flops; ck_hr u_hr/ck_head
# (R 303.1) 363.2 ps.  This wrapper measures a hard-child clock-pin leaf at pin arrival + its record insertion, the
# same quantity the gate judges, so the engine's own balance loop pads the root to the child flops.
#
# Contract (fail closed): sourced right after clock_spine.tcl; ::ot_sp_child_ins = {"master/pin" ps} from
# domain_spatial_spine.child_insertion_targets; OT_SPINE_MACRO_LEAF=1 and OT_SPINE_MACRO_PIN_LEAF=1 (each hard-child
# clock pin is its own one-member leaf, so the offset never moves a flop).  No SDC, latency, target or engine change.
if {![info exists ::ot_sp_child_ins] || ![dict size $::ot_sp_child_ins]} { error "OT_DSCI: ::ot_sp_child_ins empty" }
if {[info procs ot_sp_leaf_arrivals] eq "" || [info procs ot_sp_env] eq ""} { error "OT_DSCI: clock_spine.tcl not loaded" }
if {[ot_sp_env OT_SPINE_MACRO_LEAF 0] ne "1" || [ot_sp_env OT_SPINE_MACRO_PIN_LEAF 0] ne "1"} {
  error "OT_DSCI: child insertion requires OT_SPINE_MACRO_LEAF=1 and OT_SPINE_MACRO_PIN_LEAF=1"
}
if {[info procs ot_dsci_leaf_arrivals_base] eq ""} {
  rename ot_sp_leaf_arrivals ot_dsci_leaf_arrivals_base
  proc ot_sp_leaf_arrivals {} {
    set a [ot_dsci_leaf_arrivals_base]
    set hit 0
    dict for {id its} $::ot_sp_members {
      if {![dict exists $a $id]} continue
      set keyed {}
      foreach it $its {
        set inst [$it getInst]
        if {![[$inst getMaster] isBlock]} continue
        set key "[[$inst getMaster] getName]/[[$it getMTerm] getName]"
        if {[dict exists $::ot_sp_child_ins $key]} { lappend keyed $key }
      }
      if {![llength $keyed]} continue
      if {[llength $its] != 1} { error "OT_DSCI: leaf $id mixes a hard-child clock pin with other sinks ([llength $its])" }
      dict set a $id [expr {[dict get $a $id] + [dict get $::ot_sp_child_ins [lindex $keyed 0]]}]
      incr hit
    }
    if {![info exists ::ot_dsci_reported] || $::ot_dsci_reported != $hit} {
      puts "OT_DSCI child-flop leaves: $hit hard-child clock pins measured at pin + record insertion"
      set ::ot_dsci_reported $hit
    }
    return $a
  }
}
puts "OT_DSCI child insertion targets: $::ot_sp_child_ins"
