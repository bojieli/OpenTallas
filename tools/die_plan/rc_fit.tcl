# rc_fit.tcl (HBM-CORES 2026-10-25): fit a per-design RC scale so the GRT-stage parasitic estimate reproduces routed RCX
# clock arrival per sink (QC cqb finding F2: estimate - RCX = +11..+45 ps per sink). Inputs (env): OT_CORNER (FF/TT),
# OT_GRT_ODB, OT_SDC, OT_RCX_TSV (CK<TAB>pin<TAB>arrival_ps from the routed RCX view), OT_SCALES ("r:c r:c ..."),
# OT_LAYERS (M2-M7), OT_OUT, optional OT_GRT_ARGS (extra global_route args so the estimate matches the flow's GRT, e.g.
# "-resistance_aware -congestion_iterations 30" for ORFS ENABLE_RESISTANCE_AWARE runs; S81-HEAD 10-25: without it the
# elemB estimate was +87 ps vs RCX instead of the flow's +36). Writes per scale: mean/p95/max |est-rcx| over sinks and the scaled setRC file.
set C $::env(OT_CORNER)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_${C}_*] { read_liberty $l }
foreach l [glob -nocomplain /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_${C}_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_${C}_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
foreach l [split [expr {[info exists ::env(OT_EXTRA_LIBS)] ? $::env(OT_EXTRA_LIBS) : ""}]] { if {$l ne ""} { read_liberty $l } }
read_db $::env(OT_GRT_ODB)
read_sdc $::env(OT_SDC)
set L $::env(OT_LAYERS)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal $L -clock $L
set_global_routing_layer_adjustment $L 0.5
global_route -allow_congestion {*}[expr {[info exists ::env(OT_GRT_ARGS)] ? $::env(OT_GRT_ARGS) : ""}]
set_propagated_clock [all_clocks]
array set rcx {}
set f [open $::env(OT_RCX_TSV)]
while {[gets $f line] >= 0} { set p [split $line "\t"]; if {[lindex $p 0] eq "CK" && [lindex $p 2] ne ""} { set rcx([lindex $p 1]) [expr {[lindex $p 2] * $::env(OT_RCX_UNIT)}] } }
close $f
set base_layer {M1 {7.04175E-02 1e-10} M2 {2.97127E-02 1.74942E-01} M3 {3.12870E-02 1.55554E-01} M4 {1.80365E-02 1.78475E-01} M5 {1.89935E-02 1.64264E-01} M6 {1.18796E-02 1.87426E-01} M7 {1.25096E-02 1.62979E-01} M8 {8.44765E-03 1.03962E-01} M9 {8.89556E-03 9.28446E-02}}
set out [open $::env(OT_OUT)/rc_fit.tsv w]
puts $out "scale_r\tscale_c\tn\tmean\tmean_abs\tp95_abs\tmax_abs\thold_wns\thold_n"
foreach sc [split $::env(OT_SCALES)] {
  lassign [split $sc :] sr scap
  set rc [open $::env(OT_OUT)/setRC_r${sr}_c${scap}.tcl w]
  foreach {ly v} $base_layer { lassign $v r c; puts $rc "set_layer_rc -layer $ly -resistance [expr {$r*$sr}] -capacitance [expr {$c*$scap}]" }
  puts $rc "set_wire_rc -signal -resistance [expr {2.65684E-02*$sr}] -capacitance [expr {1.65790E-01*$scap}]"
  puts $rc "set_wire_rc -clock -resistance [expr {2.14161E-02*$sr}] -capacitance [expr {1.45426E-01*$scap}]"
  foreach {v r} {V1 1.72E-02 V2 1.72E-02 V3 1.72E-02 V4 1.18E-02 V5 1.18E-02 V6 8.20E-03 V7 8.20E-03 V8 6.30E-03 V9 6.30E-03} { puts $rc "set_layer_rc -via $v -resistance [expr {$r*$sr}]" }
  close $rc
  source $::env(OT_OUT)/setRC_r${sr}_c${scap}.tcl
  estimate_parasitics -global_routing
  set d {}
  foreach p [all_registers -clock_pins] {
    set n [get_full_name $p]
    if {![info exists rcx($n)]} continue
    set a ""; catch {set a [get_property $p arrival_max_rise]}
    if {$a eq ""} continue
    lappend d [expr {$a - $rcx($n)}]
  }
  set n [llength $d]; set s 0; set sa 0; set ab {}
  foreach x $d { set s [expr {$s+$x}]; set sa [expr {$sa+abs($x)}]; lappend ab [expr {abs($x)}] }
  set ab [lsort -real $ab]
  puts $out [format "%s\t%s\t%d\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%d" $sr $scap $n [expr {$s/$n}] [expr {$sa/$n}] [lindex $ab [expr {int(0.95*$n)}]] [lindex $ab end] [sta::time_sta_ui [sta::worst_slack_cmd min]] [sta::endpoint_violation_count min]]
  flush $out
}
close $out
puts RC_FIT_DONE
