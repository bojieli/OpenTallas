# tt_setup_repair.tcl (FABLE-PD-HEAD-1650 finding 1, COORD r190): setup repair in a TT scene.
# Class: every kit (S81, QC, KV, HEAD; 65 recent kits read) runs CTS with SKIP_CTS_REPAIR_TIMING=1 and the GRT-stage repair_timing in an
# FF-only session (read_liberty -corner bc): "RSZ-0098 No setup violations found" while the TT gate of the same DB reads -77.72 / -261.02.
# TT setup is measured, never optimised.  This step runs between CTS and GRT (run_kit.sh, only when the kit has tt_setup_repair.on, gen env
# OT_TT_SETUP_REPAIR=1): open 4_cts.odb with the TC libraries and the kit SDC with the vclk bound for TT (the postcts_gate.tcl frame),
# repair_timing -setup only (hold repair stays in the FF GRT session; SETUP_SLACK_MARGIN is NOT used: the hold call shares it), legalize,
# write the repaired 4_cts.odb.  env ODB (input), OUT (output, default = ODB), OT_TT_SETUP_MARGIN (ps, default 0), OT_TT_SETUP_ARGS (extra).
if {[file exists /work/config.mk]} {
  set fh [open /work/config.mk]
  foreach ln [split [read $fh] "\n"] {
    if {[regexp {^export\s+(OT_VCLK_TT|LAYER_PARASITICS_FILE)\s*\??=\s*(\S+)} $ln -> k v] && ![info exists ::env($k)]} { set ::env($k) $v }
  }
  close $fh
}
proc ot_tt_libs {} {
  set output [exec bash -c {source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 || exit; exec make --no-print-directory -s -C /OpenROAD-flow-scripts/flow "DESIGN_CONFIG=/work/config.mk" "print-TC_LIB_FILES"}]
  set recs {}
  foreach line [split $output \n] { if {[regexp {^TC_LIB_FILES\s*[:=]\s*(.*)$} $line -> v]} { lappend recs $v } }
  if {[llength $recs] != 1} { error "tt_setup_repair: missing or ambiguous make TC_LIB_FILES" }
  return [regexp -all -inline {\S+} [lindex $recs 0]]
}
foreach f [ot_tt_libs] {
  set g [file join [file dirname [file dirname $f]] .busfit [file tail $f]]
  if {[file exists $g]} { set c [open $g]; gets $c h; close $c; if {[string first [lindex [exec sha256sum -- $f] 0] $h] >= 0} { set f $g } }
  read_liberty $f
}
read_db $::env(ODB)
read_sdc /work/constraint.sdc
set virt {}; set real {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend virt $c } else { lappend real $c } }
if {[llength $virt] != 1} { error "tt_setup_repair: expected exactly one source-less virtual IO clock" }
if {[info exists ::env(OT_VCLK_TT)]} { set_clock_latency -source $::env(OT_VCLK_TT) $virt }
set_propagated_clock $real
if {[info exists ::env(LAYER_PARASITICS_FILE)] && [file exists $::env(LAYER_PARASITICS_FILE)]} { source $::env(LAYER_PARASITICS_FILE) } else { source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl }
estimate_parasitics -placement
proc ot_tt_wns {tag} {
  set w [sta::worst_slack -max]; set t [sta::total_negative_slack -max]
  puts [format "OT_TT_SETUP_REPAIR %s TT setup wns %.2f tns %.2f" $tag $w $t]
  return [list $w $t]
}
lassign [ot_tt_wns before] w0 t0
set mg 0; if {[info exists ::env(OT_TT_SETUP_MARGIN)] && $::env(OT_TT_SETUP_MARGIN) ne ""} { set mg $::env(OT_TT_SETUP_MARGIN) }
set extra {}; if {[info exists ::env(OT_TT_SETUP_ARGS)]} { set extra $::env(OT_TT_SETUP_ARGS) }
set n0 [llength [get_cells *]]
if {$w0 < $mg} {
  repair_timing -setup -setup_margin $mg -repair_tns 100 -skip_last_gasp -verbose {*}$extra
  detailed_placement
  estimate_parasitics -placement
}
lassign [ot_tt_wns after] w1 t1
puts "OT_TT_SETUP_REPAIR cells [expr {[llength [get_cells *]] - $n0}] added; wns [format %.2f $w0] -> [format %.2f $w1] tns [format %.2f $t0] -> [format %.2f $t1]"
set out $::env(ODB); if {[info exists ::env(OUT)] && $::env(OUT) ne ""} { set out $::env(OUT) }
write_db $out
puts "OT_TT_SETUP_REPAIR wrote $out"
