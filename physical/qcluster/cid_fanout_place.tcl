# SQC-CB16c 2026-10-22 (PENDING-COORD diagnostic) PRE_GLOBAL_PLACE: fabric register sites (OT_CID_BASE_PLACE, default
# fabric_sites_place_n.tcl) + the per-column cid buffer copies (tools/qwen_cluster/cid_fanout.py, u_cidb_c<c>_b<b>) FIRM in
# the S band at the foot of their column's outer corridor: OT_CID_SITES = "c:x:y,..." (um, bit 0 lower-left, bits stacked
# one row up each).  Released to PLACED by cid_fanout_release.tcl before DPL.  Placement only; netlist unchanged.
set ot_cid_base [expr {[info exists ::env(OT_CID_BASE_PLACE)] && $::env(OT_CID_BASE_PLACE) ne "" ? $::env(OT_CID_BASE_PLACE) : "[file dirname [info script]]/fabric_sites_place_n.tcl"}]
source $ot_cid_base
set blk [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set site_w 0.054; set row_h 0.27
set ot_cid_n 0
foreach spec [split $::env(OT_CID_SITES) ","] {
  lassign [split $spec ":"] c x y
  for {set b 0} {$b < 12} {incr b} {
    set inst [$blk findInst "u_cidb_c${c}_b${b}"]
    if {$inst eq "NULL"} { error "OT_CID: u_cidb_c${c}_b${b} not found (netlist not from cid_fanout.py?)" }
    set xs [expr {round(round($x / $site_w) * $site_w * $dbu)}]
    set ys [expr {round(round(($y + $b * $row_h) / $row_h) * $row_h * $dbu)}]
    $inst setLocation $xs $ys
    $inst setPlacementStatus FIRM
    incr ot_cid_n
  }
}
puts "OT_CID placed $ot_cid_n cid buffer copies FIRM ($::env(OT_CID_SITES))"
