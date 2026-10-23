# SQC-CB16c 2026-10-22 PRE_DETAIL_PLACE: fabric_sites_release.tcl + release the cid buffer copies (cid_fanout_place.tcl).
source [file dirname [info script]]/fabric_sites_release.tcl
set ot_cid_r 0
foreach inst [[ord::get_db_block] getInsts] {
  if {[string match "u_cidb_c*" [$inst getName]] && [$inst getPlacementStatus] eq "FIRM"} { $inst setPlacementStatus PLACED; incr ot_cid_r }
}
puts "OT_CID released $ot_cid_r cid buffer copies for DPL"
