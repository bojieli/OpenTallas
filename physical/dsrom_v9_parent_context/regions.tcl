# Whole actual S81 slot; parent placement stays outside the full Z18 reservation.
set block [ord::get_db_block]
set scale [$block getDbUnitsPerMicron]
set region [odb::dbRegion_create $block v9_parent]
$region setRegionType EXCLUSIVE
set box {};foreach x {2.16 2.16 525.096 237.60} {lappend box [expr {round($x*$scale)}]}
odb::dbBox_create $region {*}$box
set group [odb::dbGroup_create $block v9_parent];$region addGroup $group
set area 0.;set count 0
foreach inst [$block getInsts] {
 set master [$inst getMaster]
 if {[$master isBlock]} {error "unexpected reduced or unqualified macro"}
 if {[regexp {SPACER|WELLTAP} [$master getType]]} {continue}
 $group addInst $inst
 set area [expr {$area+double([$master getWidth])*[$master getHeight]/$scale/$scale}]
 incr count
}
puts "V9_PARENT_REGION cells=$count area_um2=$area reserved_QX_frame=510.84x151.2"
if {$area>61560} {error "parent mapped cells exceed half-density region capacity"}
