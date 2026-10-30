# Die-edge PHY is fixed at the exact reviewed parent-plan rectangle.
# The plan has no outside-die channel; do not let the macro-placer invent one.
set b [ord::get_db_block]
set dbu [$b getDbUnitsPerMicron]
set i [$b findInst {u_bound.u_io_ucie}]
if {$i eq "NULL" || $i eq ""} {error {COLLPHY_EXACT missing u_bound.u_io_ucie}}
set m [$i getMaster]
set wanted [expr {round(777.6*$dbu)}]
if {[$m getWidth]!=$wanted || [$m getHeight]!=$wanted} {error {COLLPHY_EXACT master size != parent plan}}
$i setOrient R0
$i setLocation 0 0
$i setPlacementStatus LOCKED
set r [$i getBBox]
set c [$b getCoreArea]
if {[$r xMin]!=0 || [$r yMin]!=0 || [$r xMax]!=$wanted || [$r yMax]!=$wanted} {error {COLLPHY_EXACT bbox != parent plan}}
if {[$r xMin]<[$c xMin] || [$r yMin]<[$c yMin] || [$r xMax]>[$c xMax] || [$r yMax]>[$c yMax]} {error {COLLPHY_EXACT outside core}}
puts "COLLPHY_EXACT_PASS master=[$m getName] bbox=[$r xMin],[$r yMin],[$r xMax],[$r yMax] dbu=$dbu LOCKED"
