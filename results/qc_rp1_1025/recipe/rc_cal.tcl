# QC-RP1 10-25 F2: GRT wire RC calibrated to routed RCX (QC-CQB2 fit on qfd_dv_s8x_vmr, intel1 qc-cqb/vmr_s5/rcfit:
# kR 0.8 / kC 0.9 on setRC.tcl layer RC -> clock arrival est-RCX mean TT +5.6 / FF +2.1 ps, hold-slack bias -2.3 ps;
# uncalibrated 1/1 was +25.3 / +20.6).  Provisional (fit on a sibling core) until rp1's own routed fit.
set rcc_k [expr {[info exists ::env(OT_RC_K)] ? $::env(OT_RC_K) : "0.8 0.9"}]
lassign $rcc_k rcc_r rcc_c
foreach {l r c} {M1 7.04175E-02 1e-10 M2 2.97127E-02 1.74942E-01 M3 3.12870E-02 1.55554E-01 M4 1.80365E-02 1.78475E-01 M5 1.89935E-02 1.64264E-01 M6 1.18796E-02 1.87426E-01 M7 1.25096E-02 1.62979E-01} {
  set_layer_rc -layer $l -resistance [expr {$r*$rcc_r}] -capacitance [expr {$c*$rcc_c}]
}
foreach v {V1 V2 V3} { set_layer_rc -via $v -resistance [expr {1.72E-02*$rcc_r}] }
foreach v {V4 V5} { set_layer_rc -via $v -resistance [expr {1.18E-02*$rcc_r}] }
puts "OT_RC_CAL kR $rcc_r kC $rcc_c"
