# tap_window_measure.tcl: print the OT_TAP_RC line (per clock port mean(min-max,sinks)) of a kit's 4_cts.odb
# (S81-COL-CLK-1116 spec 0b); feed the output to tap_window_measure.py --log.
# env: FX_ODB (db name under /base), FX_SDC (default /sdc/golden.sdc), FX_SCALE (signal cap scale, default 1.0),
#      OT_CORE_LAT (core_latency.txt), OT_TAP_TARGET_PS; kit tools dir /work holds clock_family.tcl, tap_balance.tcl, setRC_rcx.tcl.
read_db /base/$::env(FX_ODB)
read_sdc [expr {[info exists ::env(FX_SDC)] ? $::env(FX_SDC) : "/sdc/golden.sdc"}]
source /work/setRC_rcx.tcl
set fx_scale [expr {[info exists ::env(FX_SCALE)] ? $::env(FX_SCALE) : 1.0}]
set_wire_rc -signal -resistance 2.88205E-02 -capacitance [expr {1.40190E-01*$fx_scale}]
set ::env(OT_TAP_REPORT_ONLY) 1
set_propagated_clock [all_clocks]
estimate_parasitics -placement
source /work/clock_family.tcl
source /work/tap_balance.tcl
