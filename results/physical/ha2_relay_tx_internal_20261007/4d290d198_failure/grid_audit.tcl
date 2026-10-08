read_db /r/results/asap7/ha2_relay_tx_internal/base/3_5_place_dp-failed.odb
set b [ord::get_db_block]
set r [lindex [$b getRows] 0];set s [$r getSite]
puts "ROW origin=[$r getOrigin] site_w=[$s getWidth] site_h=[$s getHeight] spacing=[$r getSpacing]"
foreach r [$b getRegions] {puts "REGION [$r getName] type=[$r getRegionType]";foreach box [$r getBoundaries] {puts "BOX [$box xMin] [$box yMin] [$box xMax] [$box yMax]"}}
foreach i [$b getInsts] {
 if {[string match {*next_return*} [$i getName]] && [regexp {DFF} [[$i getMaster] getName]]} {puts "CELL [$i getName] origin=[$i getOrigin] group=[$i getGroup]"}
}
exit
