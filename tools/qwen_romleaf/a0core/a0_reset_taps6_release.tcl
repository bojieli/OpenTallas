# Multi-level synchronous reset is opt-in; the legacy hook remains unchanged for existing kits.
if {[info exists ::env(OT_RST_LAND_DISTRIBUTED)] && $::env(OT_RST_LAND_DISTRIBUTED) eq "1"} {
  source /src/tools/qwen_romleaf/a0core/a0_reset_paths_release.tcl
  return
}
# QC-P6-A0 10-23 A0 v6: PRE_DETAIL_PLACE release of the per-tap reset landing copies (a0_reset_taps6.tcl) for DPL.
set rt6r_blk [ord::get_db_block]
set rt6r_n 0
set rt6r_fn [expr {[string match "/*" $::env(OT_A0_RST_TAPS)] ? $::env(OT_A0_RST_TAPS) : "/src/$::env(OT_A0_RST_TAPS)"}]
set rt6r_f [open $rt6r_fn r]
while {[gets $rt6r_f line] >= 0} {
  if {[string match "#*" $line] || [string trim $line] eq ""} continue
  set ins [$rt6r_blk findInst [lindex [split $line "\t"] 0]]
  if {$ins ne "NULL" && [$ins getPlacementStatus] eq "FIRM"} { $ins setPlacementStatus PLACED; incr rt6r_n }
}
close $rt6r_f
puts "OT_A0_RESET_TAPS released $rt6r_n copies to DPL"
