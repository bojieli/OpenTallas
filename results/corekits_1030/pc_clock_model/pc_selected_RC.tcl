# setRC_rcx_asap7.tcl -- ASAP7 per-layer wire RC calibrated so the GRT-stage estimate (estimate_parasitics
# -global_routing on 5_1_grt.odb) reproduces routed OpenRCX (rcx_patterns.rules, 6_final.spef) clock-sink arrivals.
# Lane FLOW 2026-10-25, tools/die_plan/rc_calib.py (+ rc_calib_probe.tcl, rc_calib_wire_dump.py, rc_calib_run.sh).
#
# Method. (1) Per-layer least squares of RCX net totals vs routed length per layer (6_final.odb wires, nets >= 5 um):
#   R: RCX unit R and via R equal the stock setRC values to <0.5% on every layer/run -> R and vias kept stock.
#   C: RCX unit C is BELOW stock on M3-M7 and clock nets (no NDR on ~99% of them) see less C than signal nets:
#        fit fF/um     M2     M3     M4     M5     M6     M7      (stock .175 .156 .178 .164 .187 .163)
#        clock nets  .12-.17 .13-.20 .10-.13 .075-.13 .132 .087   (ve_m_m5, rr_h0_c, argmax_r2, ve_s_m0, vmr_cqb)
#        signal nets .16-.22 .12-.16 .12-.21 .09-.16  .120 .132
#   GRT guide length per clock net matches routed length (<3%), so the bias is unit C, not route detour.
# (2) Candidate per-layer C tables between the clock and signal fits, judged by the final criterion: est-minus-RCX
#   clock-sink arrival over 5 routed runs x TT/FF. This file = midpoint of the clock-weighted (calB) and
#   compromise (calC) tables; C fit on ve_m_m5, rr_h0_c, argmax_r2; ve_s_m0, vmr_cqb held out of the
#   C fit (the B/C midpoint was picked after seeing all 5 runs).
# Result (est - RCX clock arrival, ps, mean / p95|.|): stock +15..+33 / 18..37 -> this file |mean| <= 4.5, p95 4.4..13.4 (worst: vmr_cqb, held out).
#   Full table: results/flow_1025/rc_calib.json.
# Caveat: one table serves TT and FF (the error is corner-independent within ~1-6 ps). Long SIGNAL nets get a more
#   optimistic estimate than stock (stock already -1..-17 ps on the 150 longest nets; this file -5..-28 ps), because
#   on M4/M5 signal nets carry more coupling C than clock nets and set_layer_rc cannot tell them apart.
# FLOW-RC-1 2026-10-27 (lanes/FLOW-RC.md): PER-CLASS records (fail-closed guard tools/die_plan/core_flow.check_rc_cal).
#   OpenROAD 26Q3 set_layer_rc (GRT / estimate_parasitics -global_routing basis) has no -signal/-clock form; only
#   set_wire_rc (placement / CTS estimate) is per class.  Measured on 4 designs (HBM collar a4/a5, S81 rr_h1_c, QC rst3_k0,
#   HEAD elemA_eco; routed 6_final geometry vs RCX SPEF): RCX unit R and via R = stock to <0.5 % for both classes;
#   per-layer unit C SIGNAL (len-weighted) M2 .157 M3 .132 M4 .148 M5 .114, CLOCK M2 .115 M3 .151 M4 .115 M5 .096 fF/um.
#   A signal-C set_layer_rc moves the GRT clock-sink arrival estimate vs RCX from +0.1/+6.6/+4.8 to +2.9/+14.9/+12.5 ps
#   (a4/QC/S81 TT mean), so the per-layer table below stays the CLOCK-arrival calibration; the signal class gets its own
#   set_wire_rc -signal (= the measured signal unit R/C, M2-M5 routed-length weighted).  The GRT signal slew gap on long
#   via-dense M2/M3 nets (collar a4: est 197-261 ps vs RCX 324-369 ps) is route topology (DRT ~0.9 via/um), not unit RC:
#   no per-layer table closes it (signal C + M2/M3 R x1.3 still 0 est viol vs 32 RCX) -> handled by the routed-RCX DRV
#   gate + placement max-wire repair, not by this file.
# OT_RC_CAL signal set_wire_rc -signal = RCX unit R/C fit on SIGNAL nets >= 5 um, 4 designs (FLOW-RC-1 2026-10-27); GRT basis shares the per-layer table
# OT_RC_CAL clock set_layer_rc per layer = clock-sink arrival fit (FLOW 2026-10-25, rc_calib.json); set_wire_rc -clock unchanged
set_layer_rc -layer M1 -resistance 7.04175E-02 -capacitance 1.00000E-10
set_layer_rc -layer M2 -resistance 2.97127E-02 -capacitance 1.67500E-01
set_layer_rc -layer M3 -resistance 3.12870E-02 -capacitance 1.31500E-01
set_layer_rc -layer M4 -resistance 1.80365E-02 -capacitance 1.27500E-01
set_layer_rc -layer M5 -resistance 1.89935E-02 -capacitance 9.80000E-02
set_layer_rc -layer M6 -resistance 1.18796E-02 -capacitance 1.30500E-01
set_layer_rc -layer M7 -resistance 1.25096E-02 -capacitance 9.25000E-02
set_layer_rc -layer M8 -resistance 8.44765E-03 -capacitance 1.03962E-01
set_layer_rc -layer M9 -resistance 8.89556E-03 -capacitance 9.28446E-02
set_wire_rc -signal -resistance 2.88205E-02 -capacitance 1.40190E-01
set_wire_rc -clock -resistance 2.14161E-02 -capacitance 1.13298E-01
set_layer_rc -via V1 -resistance 1.72000E-02
set_layer_rc -via V2 -resistance 1.72000E-02
set_layer_rc -via V3 -resistance 1.72000E-02
set_layer_rc -via V4 -resistance 1.18000E-02
set_layer_rc -via V5 -resistance 1.18000E-02
set_layer_rc -via V6 -resistance 8.20000E-03
set_layer_rc -via V7 -resistance 8.20000E-03
set_layer_rc -via V8 -resistance 6.30000E-03
set_layer_rc -via V9 -resistance 6.30000E-03

# Optional checkpoint when the native setup repair restores this RC baseline.
# No RC assignments, timing constraints or physical design edits below.
if {[info exists ::ot_mm_synced] && $::ot_mm_synced && ![info exists ::codex_pc_native_saved] && [llength [info commands grt::have_routes]]} {
 if {[grt::have_routes]} {
  set ::codex_pc_native_saved 1
  if {[catch {
   write_db /work/pc_native_after_setup.odb
   write_sdc -no_timestamp /work/pc_native_after_setup.sdc
   write_guides /work/pc_native_after_setup.guide
   if {[llength [info commands write_global_route_segments]]} {write_global_route_segments /work/pc_native_after_setup.segments}
  } e]} {puts "PC_OPTIONAL_NATIVE_CHECKPOINT_FAIL $e"} else {puts PC_NATIVE_AFTER_SETUP_CHECKPOINT_SAVED}
 }
}
