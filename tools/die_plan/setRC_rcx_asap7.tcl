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
set_layer_rc -layer M1 -resistance 7.04175E-02 -capacitance 1.00000E-10
set_layer_rc -layer M2 -resistance 2.97127E-02 -capacitance 1.67500E-01
set_layer_rc -layer M3 -resistance 3.12870E-02 -capacitance 1.31500E-01
set_layer_rc -layer M4 -resistance 1.80365E-02 -capacitance 1.27500E-01
set_layer_rc -layer M5 -resistance 1.89935E-02 -capacitance 9.80000E-02
set_layer_rc -layer M6 -resistance 1.18796E-02 -capacitance 1.30500E-01
set_layer_rc -layer M7 -resistance 1.25096E-02 -capacitance 9.25000E-02
set_layer_rc -layer M8 -resistance 8.44765E-03 -capacitance 1.03962E-01
set_layer_rc -layer M9 -resistance 8.89556E-03 -capacitance 9.28446E-02
set_wire_rc -signal -resistance 2.65684E-02 -capacitance 1.29163E-01
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
