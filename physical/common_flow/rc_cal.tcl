# LAYER_PARASITICS_FILE wrapper (QC-CQB2 2026-10-25, opt-in): RC CORRELATION of the estimated wire parasitics to the routed RCX view.
#
# Why (qfd_dv_s8x_vmr_cqb, routed review claude/qc-cqb-1025@8940062a7): with the platform setRC.tcl layer RC, the
# GRT-guide estimate (estimate_parasitics -global_routing) of the clock arrival at every sink was +11.6..+45.2 ps TT
# (mean +25.3) above the routed RCX (6_final.spef) value, and the FF hold slack of near-critical endpoints was off by
# -29..+32 ps.  Every pre-route decision taken on that estimate (CTS balance, GRT-stage hold repair, the core latency I)
# moved after route: GRT hold +1.05 -> RCX -13.2 ps / 162 endpoints.
# Fit (rc_fit.tcl on that routed DB, 3711 sinks, kR x kC grid over M1-M7 + V1-V5): kR 0.8 / kC 0.9 gives clock-arrival
# error TT mean +5.6 (-10.8..+24.6), FF +2.1 (-12.3..+18.3); FF hold-slack error (est - RCX, endpoints with RCX
# slack < 30 ps) median +1.1, p5 -9.3, p95 +11.4 ps.  The remaining spread is path-geometry dependent (long unbalanced
# runs), not a scale: structured, equal-length clock distribution (mscts_core.tcl) plus a hold margin >= the p95 error is
# the cure for that part.
#
# Use: export LAYER_PARASITICS_FILE = <this file> (ORFS load.tcl sources it in place of the platform setRC.tcl) and OT_RC_CAL = "kR,kC" (H and V layers alike) or "kRh,kCh,kRv,kCv".  Unset or
# empty OT_RC_CAL: the platform values unchanged (opt-in).  Affects only ESTIMATED parasitics (placement / GRT); RCX
# sign-off extraction never reads it.  OT_RC_BASE: the platform setRC.tcl (default asap7).
set ot_rcc_base [expr {[info exists ::env(OT_RC_BASE)] && $::env(OT_RC_BASE) ne "" ? $::env(OT_RC_BASE) : "/OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl"}]
source $ot_rcc_base
if {[info exists ::env(OT_RC_CAL)] && $::env(OT_RC_CAL) ne ""} {
  set ot_rcc_k [split $::env(OT_RC_CAL) ,]
  if {[llength $ot_rcc_k] == 2} { lappend ot_rcc_k {*}$ot_rcc_k }
  if {[llength $ot_rcc_k] != 4} { error "OT_RC_CAL: want kR,kC or kRh,kCh,kRv,kCv, got $::env(OT_RC_CAL)" }
  lassign $ot_rcc_k ot_rcc_rh ot_rcc_ch ot_rcc_rv ot_rcc_cv
  # asap7 setRC.tcl layer values (M2/M4/M6 horizontal, M1/M3/M5/M7 vertical); M8/M9 die-level only, unscaled
  foreach {l r c} {M1 7.04175E-02 1e-10 M2 2.97127E-02 1.74942E-01 M3 3.12870E-02 1.55554E-01 M4 1.80365E-02 1.78475E-01
                   M5 1.89935E-02 1.64264E-01 M6 1.18796E-02 1.87426E-01 M7 1.25096E-02 1.62979E-01} {
    if {$l in {M2 M4 M6}} { set kr $ot_rcc_rh; set kc $ot_rcc_ch } else { set kr $ot_rcc_rv; set kc $ot_rcc_cv }
    set_layer_rc -layer $l -resistance [expr {$r * $kr}] -capacitance [expr {$c * $kc}]
  }
  foreach v {V1 V2 V3} { set_layer_rc -via $v -resistance [expr {1.72E-02 * $ot_rcc_rh}] }
  foreach v {V4 V5} { set_layer_rc -via $v -resistance [expr {1.18E-02 * $ot_rcc_rh}] }
  # placement-stage wire RC (CTS characterisation, placement estimates) scaled alike
  set_wire_rc -signal -resistance [expr {2.65684E-02 * $ot_rcc_rh}] -capacitance [expr {1.65790E-01 * $ot_rcc_ch}]
  set_wire_rc -clock -resistance [expr {2.14161E-02 * $ot_rcc_rh}] -capacitance [expr {1.45426E-01 * $ot_rcc_ch}]
  puts "OT_RC_CAL layer RC scaled: R h$ot_rcc_rh v$ot_rcc_rv, C h$ot_rcc_ch v$ot_rcc_cv (estimates only; RCX unaffected)"
}
