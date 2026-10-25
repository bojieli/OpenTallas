# QC-P6-A0 10-23 A0 v6 per-tap reset landing (GEOM-REVIEW7 18:34 FIX (2); KV kv-p5-tool @0d8b36ab6 reset_taps pattern).
# PRE_GLOBAL_PLACE, after the pin flops are fixed (spec pin_hook_after_flops).  The core reset lands at the E-face pin
# (rst_n__ot_rl0, io_flop_at_pins) and its LAST landing stage is already a family of identical copies (rst_n__ot_rl1 +
# ot_rrs__rst_n__ot_rlv__c<k>: OT_RST_LAND_COPIES + reset_relay_split, <= 32 loads each; RTL body unchanged).  In v5 GPL
# left each copy at its loads' centroid, on whatever tap happened to be nearest.  Here every copy goes FIRM to the
# interior clock tap nearest its v5 placed site (table OT_A0_RST_TAPS from gen_a0c6_taps.py: inst, tap, x, y), so each
# copy is a sink of that tap's own local tree (a0_clock_taps6.tcl nearest-tap rule) at minimum insertion; copies sharing
# a tap sit side by side.  a0_reset_taps6_release.tcl hands them back to DPL (PLACED) for legalisation.
set rt6_blk [ord::get_db_block]
set rt6_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set rt6_fn [expr {[string match "/*" $::env(OT_A0_RST_TAPS)] ? $::env(OT_A0_RST_TAPS) : "/src/$::env(OT_A0_RST_TAPS)"}]
set rt6_n 0; set rt6_miss {}
set rt6_slot {}
set rt6_f [open $rt6_fn r]
while {[gets $rt6_f line] >= 0} {
  if {[string match "#*" $line] || [string trim $line] eq ""} continue
  lassign [split $line "\t"] iname tap x y
  set ins [$rt6_blk findInst $iname]
  if {$ins eq "NULL"} { lappend rt6_miss $iname; continue }
  set k [expr {[dict exists $rt6_slot $tap] ? [dict get $rt6_slot $tap] : 0}]
  dict set rt6_slot $tap [expr {$k + 1}]
  # side by side along the row: +/- 1.08 um per copy, rows of 4, beside the tap point
  set dx [expr {(($k % 4) - 1.5) * 1.08}]
  set dy [expr {($k / 4) * 0.27}]
  $ins setLocation [expr {int(round(($x + $dx) * $rt6_dbu))}] [expr {int(round(($y + $dy) * $rt6_dbu))}]
  $ins setPlacementStatus FIRM
  incr rt6_n
}
close $rt6_f
puts "OT_A0_RESET_TAPS $rt6_n reset landing copies FIRM at [dict size $rt6_slot] taps: $rt6_slot; missing [llength $rt6_miss] $rt6_miss"
if {[llength $rt6_miss]} { puts "OT_A0_RESET_TAPS WARN: [llength $rt6_miss] table instances not in the netlist ($rt6_fn)" }
