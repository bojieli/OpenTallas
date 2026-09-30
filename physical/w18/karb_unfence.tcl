# W18b: drop the slice fences (karb_pregion_fence.tcl) before detailed placement.  Global placement has
# already clustered each slice in its window; DPL's legaliser fails its region check on fence edges that
# are off the site grid and on cells the resizer added (DPL-0008/-0033), so legalisation runs unfenced.
set ot_block [ord::get_db_block]
set n 0
foreach g [$ot_block getGroups] { if {[string match "ot_slice*" [$g getName]]} { odb::dbGroup_destroy $g; incr n } }
foreach r [$ot_block getRegions] { if {[string match "ot_slice*" [$r getName]]} { odb::dbRegion_destroy $r; incr n } }
puts "OT_UNFENCE removed $n groups/regions"
