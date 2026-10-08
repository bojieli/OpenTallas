# Geometry only: parent glue is compact between the symmetric skew chains.
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set r [odb::dbRegion_create $block head_native_logic]
$r setRegionType EXCLUSIVE
odb::dbBox_create $r [expr {round(125.28*$dbu)}] [expr {round(48.60*$dbu)}] [expr {round(174.96*$dbu)}] [expr {round(89.64*$dbu)}]
set g [odb::dbGroup_create $r head_native_logic]
set n 0
foreach i [$block getInsts] {
 if {[$i isFixed] || [[$i getMaster] isBlock]} {continue}
 $g addInst $i
 incr n
}
if {$n <1000} {error "missing native parent logic: $n cells"}
puts "OT_HEAD_NATIVE_LOGIC_FENCE $n"
