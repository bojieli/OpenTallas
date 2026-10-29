read_db /work/run/results/asap7/hbc_hnx_lane_x/base/3_place.odb
set b [ord::get_db_block]
set j [$b findInst {u_bdc.jv$_DFF_PN0_}]
if {$j == "NULL"} {error "Missing exact jv data FF"}
puts "HNX_ANCHOR old=[$j getLocation] status=[$j getPlacementStatus]"
set states {}
foreach i [$b getInsts] {lappend states [list $i [$i getPlacementStatus]]; $i setPlacementStatus FIRM}
$j setPlacementStatus PLACED
$j setLocation 103032 234900
$j setPlacementStatus PLACED
detailed_placement
check_placement -verbose
foreach s $states {lassign $s i st;$i setPlacementStatus $st}
$j setPlacementStatus FIRM
puts "HNX_ANCHOR new=[$j getLocation] status=[$j getPlacementStatus]"
write_db /work/3_place_anchor.odb
set ::env(OT_GEOM_OUT) /work/anchor_geom.tsv
source /work/geom_dump.tcl
