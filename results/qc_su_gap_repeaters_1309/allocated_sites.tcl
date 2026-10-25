# Inactive until this exact allocation/image has independent geometry review.
array unset ot_gap_moved
set ot_gap_blk [ord::get_db_block]
set ot_gap_dbu [$ot_gap_blk getDbUnitsPerMicron]
set ot_gap_i [$ot_gap_blk findInst {wire2093}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(17.226*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2093) [list 17.203 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2027}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(17.334*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2027) [list 17.324 31.86 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1961}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(17.387999999999998*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1961) [list 17.384 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1895}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(17.496000000000002*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1895) [list 17.474 31.32 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1293}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(17.496000000000002*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1293) [list 17.515 624.24 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1227}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(17.496000000000002*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1227) [list 17.515 624.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1161}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(17.496000000000002*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1161) [list 17.515 624.78 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1829}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(17.55*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1829) [list 17.564 31.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1763}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(17.658*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1763) [list 17.653 30.78 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1691}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(17.712*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1691) [list 17.729 30.51 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1625}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(17.82*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1625) [list 17.818 30.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1559}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(17.874000000000002*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1559) [list 17.877 32.13 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1493}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(17.982*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1493) [list 17.965 31.86 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1427}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.036*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1427) [list 18.054 31.59 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1361}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.09*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1361) [list 18.113 29.97 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1093}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1093) [list 18.626 723.33 0.6479999999999997 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1021}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1021) [list 18.626 723.06 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire955}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire955) [list 18.626 722.79 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire889}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire889) [list 18.626 722.52 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire823}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire823) [list 18.626 722.25 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire757}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire757) [list 18.626 721.98 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire691}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire691) [list 18.626 721.71 0.6479999999999997 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire625}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire625) [list 18.626 721.44 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire559}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire559) [list 18.626 721.17 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire493}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire493) [list 18.626 720.9 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire427}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire427) [list 18.626 720.63 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire355}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire355) [list 18.626 720.36 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire319}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire319) [list 18.626 720.09 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1095}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1095) [list 18.639 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1023}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1023) [list 18.639 624.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire957}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire957) [list 18.639 624.78 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire891}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire891) [list 18.639 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire825}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire825) [list 18.639 625.32 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire759}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire759) [list 18.639 625.59 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire693}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire693) [list 18.639 625.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire627}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire627) [list 18.639 626.13 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire561}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(18.630000000000003*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire561) [list 18.639 626.4 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1295}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(19.224*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1295) [list 19.215 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1229}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(19.386*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1229) [list 19.389 31.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1163}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(19.439999999999998*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1163) [list 19.449 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1025}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(19.494*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1025) [list 19.513 31.32 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1097}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(19.548000000000002*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1097) [list 19.539 31.05 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire959}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(19.602*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire959) [list 19.628 30.78 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire495}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(19.656*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire495) [list 19.676 624.24 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire429}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(19.656*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire429) [list 19.676 624.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire357}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(19.656*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire357) [list 19.676 624.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire321}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(19.656*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire321) [list 19.676 625.05 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire893}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(19.71*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire893) [list 19.687 30.51 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire827}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(19.817999999999998*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire827) [list 19.807 30.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire761}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(19.98*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire761) [list 19.976 32.13 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire695}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.034*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire695) [list 20.035 31.86 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire629}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.142*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire629) [list 20.124 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire563}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.195999999999998*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire563) [list 20.212 31.32 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire313}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire313) [list 20.786 723.33 0.6479999999999997 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire307}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire307) [list 20.786 723.06 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire301}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire301) [list 20.786 722.79 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire295}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire295) [list 20.786 722.52 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire289}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire289) [list 20.786 722.25 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire283}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire283) [list 20.786 721.98 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire277}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire277) [list 20.786 721.71 0.6479999999999997 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire271}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire271) [list 20.786 721.44 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire259}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire259) [list 20.786 721.17 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire253}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire253) [list 20.786 720.9 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire247}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire247) [list 20.786 720.63 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire241}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire241) [list 20.786 720.36 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire235}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire235) [list 20.786 720.09 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire315}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire315) [list 20.799 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire309}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire309) [list 20.799 624.51 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire303}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire303) [list 20.799 624.78 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire297}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire297) [list 20.799 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire291}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire291) [list 20.799 625.32 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire285}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire285) [list 20.799 625.59 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire279}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire279) [list 20.799 625.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire273}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(20.79*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire273) [list 20.799 626.13 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire497}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(21.168*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire497) [list 21.164 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire431}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(21.276*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire431) [list 21.252 31.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire359}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(21.330000000000002*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire359) [list 21.338 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire261}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(21.816*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire261) [list 21.837 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire255}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(21.816*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire255) [list 21.837 624.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire249}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(21.816*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire249) [list 21.837 624.78 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire243}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(21.816*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire243) [list 21.837 625.05 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire237}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(21.816*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire237) [list 21.837 625.32 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire323}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(21.924*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire323) [list 21.934 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire317}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.032*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire317) [list 22.025 31.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire311}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.14*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire311) [list 22.114 31.59 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire305}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.194*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire305) [list 22.173 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire299}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.248*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire299) [list 22.264 31.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire293}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.356*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire293) [list 22.353 30.78 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire287}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.464*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire287) [list 22.437 30.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire281}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.518*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire281) [list 22.516 30.24 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire275}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.626*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire275) [list 22.604 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire229}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire229) [list 22.946 723.33 0.6479999999999997 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire223}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire223) [list 22.946 723.06 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire217}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire217) [list 22.946 722.79 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire211}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire211) [list 22.946 722.52 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire205}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire205) [list 22.946 722.25 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire193}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire193) [list 22.946 721.98 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire187}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire187) [list 22.946 721.71 0.6479999999999997 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire181}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire181) [list 22.946 721.44 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire175}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire175) [list 22.946 721.17 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire169}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire169) [list 22.946 720.9 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire163}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire163) [list 22.946 720.63 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire157}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire157) [list 22.946 720.36 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire151}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire151) [list 22.946 720.09 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire231}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire231) [list 22.96 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire225}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire225) [list 22.96 624.51 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire219}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire219) [list 22.96 624.78 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire213}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire213) [list 22.96 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire207}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire207) [list 22.96 625.32 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire195}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire195) [list 22.96 625.59 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire189}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(22.95*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire189) [list 22.96 625.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire263}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(23.706*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire263) [list 23.682 32.13 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire257}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(23.76*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire257) [list 23.742 31.86 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire251}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(23.814*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire251) [list 23.834 31.59 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire183}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(23.976*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire183) [list 23.998 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire177}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(23.976*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire177) [list 23.998 624.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire171}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(23.976*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire171) [list 23.998 624.78 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire165}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(23.976*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire165) [list 23.998 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire159}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(23.976*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire159) [list 23.998 625.32 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire153}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(23.976*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire153) [list 23.998 625.59 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire245}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(24.03*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire245) [list 24.011 31.32 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire239}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(24.03*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire239) [list 24.014 31.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire233}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(24.084*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire233) [list 24.074 30.78 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire227}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(24.192*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire227) [list 24.193 30.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire221}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(24.246*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire221) [list 24.237 30.24 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire215}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(24.354*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire215) [list 24.365 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire209}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(24.408*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire209) [list 24.413 31.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire197}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(24.462*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire197) [list 24.472 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire191}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(24.57*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire191) [list 24.59 29.97 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire145}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire145) [list 25.106 723.33 0.6479999999999997 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire139}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire139) [list 25.106 723.06 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire127}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire127) [list 25.106 722.79 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire121}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire121) [list 25.106 722.52 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire115}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire115) [list 25.106 722.25 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire109}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire109) [list 25.106 721.98 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire103}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire103) [list 25.106 721.71 0.6479999999999997 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire97}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire97) [list 25.106 721.44 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire91}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire91) [list 25.106 721.17 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire85}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire85) [list 25.106 720.9 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire79}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire79) [list 25.106 720.63 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire73}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire73) [list 25.106 720.36 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire61}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire61) [list 25.106 720.09 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire147}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire147) [list 25.12 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire141}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire141) [list 25.12 624.51 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire129}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire129) [list 25.12 624.78 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire123}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire123) [list 25.12 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire117}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire117) [list 25.12 625.32 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire111}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.11*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire111) [list 25.12 625.59 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire185}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.65*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire185) [list 25.633 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire179}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.704*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire179) [list 25.723 31.86 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire173}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.812*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire173) [list 25.813 31.59 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire161}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(25.974*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire161) [list 25.963 31.32 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire167}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(25.974*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire167) [list 25.987 31.05 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire155}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(26.028*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire155) [list 26.052 30.78 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire143}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire143) [list 26.13 30.51 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire149}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire149) [list 26.142 30.24 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire105}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire105) [list 26.16 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire99}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire99) [list 26.16 624.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire93}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire93) [list 26.16 624.78 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire87}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire87) [list 26.16 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire81}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire81) [list 26.16 625.32 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire75}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire75) [list 26.16 625.59 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire63}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(26.136*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire63) [list 26.16 625.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire131}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(26.298*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire131) [list 26.32 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire125}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(26.352*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire125) [list 26.369 31.86 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire113}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(26.568*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire113) [list 26.545 31.59 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire119}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(26.568*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire119) [list 26.571 29.97 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire55}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire55) [list 27.266 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire49}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire49) [list 27.266 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire43}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire43) [list 27.266 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire37}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire37) [list 27.266 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire31}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire31) [list 27.266 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire25}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire25) [list 27.266 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire19}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire19) [list 27.266 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire13}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire13) [list 27.266 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire7}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire7) [list 27.266 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3079}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3079) [list 27.266 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3073}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3073) [list 27.266 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3067}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3067) [list 27.266 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3061}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3061) [list 27.266 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire57}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire57) [list 27.28 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire51}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire51) [list 27.28 624.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire45}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire45) [list 27.28 624.78 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire39}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire39) [list 27.28 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire33}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.27*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire33) [list 27.28 625.32 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire107}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.594*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire107) [list 27.582 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire101}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.702*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire101) [list 27.703 31.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire95}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.756*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire95) [list 27.763 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire89}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(27.864*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire89) [list 27.849 31.32 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire83}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(27.918*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire83) [list 27.943 31.05 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire65}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(28.026*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire65) [list 28.023 30.78 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire77}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(28.026*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire77) [list 28.033 30.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire59}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(28.188*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire59) [list 28.206 30.24 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire53}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(28.242*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire53) [list 28.265 32.13 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire27}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(28.296*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire27) [list 28.321 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire21}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(28.296*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire21) [list 28.321 624.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire15}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(28.296*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire15) [list 28.321 624.78 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire9}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(28.296*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire9) [list 28.321 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3081}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(28.296*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3081) [list 28.321 625.32 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3075}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(28.296*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3075) [list 28.321 625.59 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire3069}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(28.296*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3069) [list 28.321 625.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3063}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(28.296*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3063) [list 28.321 626.13 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire47}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(28.404*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire47) [list 28.378 31.86 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire41}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(28.458*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire41) [list 28.437 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire35}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(28.512*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire35) [list 28.496 31.32 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3055}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3055) [list 29.426 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire3049}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3049) [list 29.426 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3043}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3043) [list 29.426 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3037}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3037) [list 29.426 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3031}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3031) [list 29.426 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3025}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3025) [list 29.426 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3013}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3013) [list 29.426 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire3007}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3007) [list 29.426 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3001}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3001) [list 29.426 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2995}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2995) [list 29.426 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2989}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2989) [list 29.426 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2983}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2983) [list 29.426 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2977}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2977) [list 29.426 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3057}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3057) [list 29.441 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3051}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3051) [list 29.441 624.51 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3045}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3045) [list 29.441 624.78 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire3039}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.43*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3039) [list 29.441 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire29}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.592*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire29) [list 29.591 32.13 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire23}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.646*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire23) [list 29.652 31.86 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire17}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.754*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire17) [list 29.77 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire3083}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(29.916*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3083) [list 29.89 31.32 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire11}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(29.97*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire11) [list 29.948 31.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3077}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.024*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3077) [list 30.005 30.78 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire3033}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3033) [list 30.482 624.24 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3027}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3027) [list 30.482 624.51 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire3015}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3015) [list 30.482 624.78 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3009}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3009) [list 30.482 625.05 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3003}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3003) [list 30.482 625.32 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2997}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2997) [list 30.482 625.59 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2991}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2991) [list 30.482 625.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2985}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2985) [list 30.482 626.13 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2979}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.456*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2979) [list 30.482 626.4 0.6479999999999997 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire3071}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(30.618*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3071) [list 30.6 32.13 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire3065}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.672*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3065) [list 30.694 31.86 0.6479999999999997 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3059}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(30.78*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3059) [list 30.754 31.59 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire3053}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.834*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3053) [list 30.843 31.32 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire3047}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(30.888*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3047) [list 30.862 31.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3041}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(30.942*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3041) [list 30.921 30.78 0.6479999999999997 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2971}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2971) [list 31.586 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2965}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2965) [list 31.586 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2959}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2959) [list 31.586 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2947}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2947) [list 31.586 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2941}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2941) [list 31.586 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2935}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2935) [list 31.586 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2929}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2929) [list 31.586 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2923}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2923) [list 31.586 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2917}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2917) [list 31.586 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2911}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2911) [list 31.586 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2905}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2905) [list 31.586 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2899}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2899) [list 31.586 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2893}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2893) [list 31.586 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2973}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2973) [list 31.601 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2967}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2967) [list 31.601 624.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2961}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(31.59*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2961) [list 31.601 624.78 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire3035}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(31.968*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3035) [list 31.961 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire3029}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.184*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3029) [list 32.172 31.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3017}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.238*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3017) [list 32.262 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire3011}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.346000000000004*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3011) [list 32.322 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire3005}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.454*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire3005) [list 32.436 31.05 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2999}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.507999999999996*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2999) [list 32.496 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2993}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.562*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2993) [list 32.555 30.51 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2949}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2949) [list 32.643 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2943}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2943) [list 32.643 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2937}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2937) [list 32.643 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2931}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2931) [list 32.643 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2925}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2925) [list 32.643 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2919}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2919) [list 32.643 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2913}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2913) [list 32.643 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2907}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2907) [list 32.643 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2901}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2901) [list 32.643 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2895}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.616*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2895) [list 32.643 626.67 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2981}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.724000000000004*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2981) [list 32.738 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2987}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.778*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2987) [list 32.764 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2975}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.832*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2975) [list 32.844 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2969}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(32.885999999999996*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2969) [list 32.909 31.59 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2963}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(32.994*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2963) [list 32.998 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2881}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2881) [list 33.746 723.33 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2875}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2875) [list 33.746 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2869}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2869) [list 33.746 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2863}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2863) [list 33.746 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2857}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2857) [list 33.746 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2851}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2851) [list 33.746 721.98 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2845}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2845) [list 33.746 721.71 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2839}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2839) [list 33.746 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2833}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2833) [list 33.746 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2827}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2827) [list 33.746 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2815}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2815) [list 33.746 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2809}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2809) [list 33.746 720.36 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2803}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2803) [list 33.746 720.09 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2883}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2883) [list 33.761 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2877}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(33.75*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2877) [list 33.761 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2951}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.074*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2951) [list 34.063 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2945}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.128*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2945) [list 34.149 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2939}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.236000000000004*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2939) [list 34.209 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2933}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.29*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2933) [list 34.299 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2927}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.397999999999996*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2927) [list 34.389 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2921}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.452*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2921) [list 34.479 30.78 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2915}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.56*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2915) [list 34.569 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2909}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.722*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2909) [list 34.742 32.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2903}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.775999999999996*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2903) [list 34.801 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2871}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2871) [list 34.804 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2865}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2865) [list 34.804 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2859}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2859) [list 34.804 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2853}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2853) [list 34.804 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2847}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2847) [list 34.804 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2841}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2841) [list 34.804 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2835}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2835) [list 34.804 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2829}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2829) [list 34.804 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2817}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2817) [list 34.804 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2811}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2811) [list 34.804 626.67 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2805}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.83*$ot_gap_dbu)}] [expr {round(626.94*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2805) [list 34.804 626.94 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2885}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(34.884*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2885) [list 34.864 31.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2897}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.884*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2897) [list 34.89 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2879}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(34.992000000000004*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2879) [list 34.978 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2797}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2797) [list 35.906 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2791}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2791) [list 35.906 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2785}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2785) [list 35.906 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2779}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2779) [list 35.906 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2773}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2773) [list 35.906 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2767}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2767) [list 35.906 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2761}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2761) [list 35.906 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2749}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2749) [list 35.906 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2743}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2743) [list 35.906 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2737}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2737) [list 35.906 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2731}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2731) [list 35.906 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2725}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2725) [list 35.906 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2719}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2719) [list 35.906 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2799}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(35.91*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2799) [list 35.922 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2873}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.018*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2873) [list 36.04 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2867}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.126000000000005*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2867) [list 36.131 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2861}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.18*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2861) [list 36.192 31.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2855}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.288*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2855) [list 36.283 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2849}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.342*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2849) [list 36.366 31.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2843}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.45*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2843) [list 36.456 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2837}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.504*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2837) [list 36.516 30.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2831}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.612*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2831) [list 36.606 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2819}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.72*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2819) [list 36.695 32.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2813}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.774*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2813) [list 36.755 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2807}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.882*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2807) [list 36.874 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2793}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2793) [list 36.965 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2787}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2787) [list 36.965 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2781}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2781) [list 36.965 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2775}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2775) [list 36.965 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2769}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2769) [list 36.965 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2763}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2763) [list 36.965 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2751}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2751) [list 36.965 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2745}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2745) [list 36.965 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2739}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2739) [list 36.965 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2733}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2733) [list 36.965 626.67 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2727}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(626.94*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2727) [list 36.965 626.94 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2721}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(36.99*$ot_gap_dbu)}] [expr {round(627.21*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2721) [list 36.965 627.21 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2801}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(37.044*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2801) [list 37.045 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2713}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2713) [list 38.066 723.33 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2707}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2707) [list 38.066 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2701}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2701) [list 38.066 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2695}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2695) [list 38.066 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2683}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2683) [list 38.066 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2677}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2677) [list 38.066 721.98 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2671}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2671) [list 38.066 721.71 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2665}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2665) [list 38.066 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2659}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2659) [list 38.066 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2653}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2653) [list 38.066 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2647}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2647) [list 38.066 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2641}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2641) [list 38.066 720.36 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2635}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2635) [list 38.066 720.09 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2795}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.07*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2795) [list 38.078 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2783}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.124*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2783) [list 38.139 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2789}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.178*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2789) [list 38.168 31.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2777}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.232*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2777) [list 38.259 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2771}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.34*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2771) [list 38.319 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2765}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.448*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2765) [list 38.44 30.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2753}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.61*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2753) [list 38.615 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2741}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(38.664*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2741) [list 38.643 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2747}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(38.664*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2747) [list 38.675 29.97 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2715}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2715) [list 39.126 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2709}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2709) [list 39.126 624.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2703}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2703) [list 39.126 624.78 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2697}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2697) [list 39.126 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2685}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2685) [list 39.126 625.32 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2679}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2679) [list 39.126 625.59 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2673}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2673) [list 39.126 625.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2667}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2667) [list 39.126 626.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2661}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2661) [list 39.126 626.4 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2655}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2655) [list 39.126 626.67 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2649}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(626.94*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2649) [list 39.126 626.94 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2643}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(39.15*$ot_gap_dbu)}] [expr {round(627.21*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2643) [list 39.126 627.21 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2735}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(39.258*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2735) [list 39.265 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2729}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(39.366*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2729) [list 39.357 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2723}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(39.42*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2723) [list 39.416 31.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2637}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.122*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2637) [list 40.139 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2629}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2629) [list 40.226 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2617}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2617) [list 40.226 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2611}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2611) [list 40.226 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2605}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2605) [list 40.226 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2599}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2599) [list 40.226 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2593}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2593) [list 40.226 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2587}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2587) [list 40.226 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2581}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2581) [list 40.226 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2575}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2575) [list 40.226 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2569}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2569) [list 40.226 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2563}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2563) [list 40.226 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2551}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2551) [list 40.226 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2545}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.23*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2545) [list 40.226 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2717}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.5*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2717) [list 40.481 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2711}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.554*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2711) [list 40.572 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2705}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.662*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2705) [list 40.663 31.59 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2699}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.77*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2699) [list 40.748 31.32 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2687}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.824*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2687) [list 40.808 31.05 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2681}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(40.932*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2681) [list 40.928 30.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2675}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(40.986*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2675) [list 40.987 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2669}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.094*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2669) [list 41.077 30.24 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2663}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(41.148*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2663) [list 41.167 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2657}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.256*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2657) [list 41.256 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2631}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2631) [list 41.287 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2619}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2619) [list 41.287 624.51 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2613}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2613) [list 41.287 624.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2607}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2607) [list 41.287 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2601}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2601) [list 41.287 625.32 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2595}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2595) [list 41.287 625.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2589}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2589) [list 41.287 625.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2583}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2583) [list 41.287 626.13 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2577}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2577) [list 41.287 626.4 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2571}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2571) [list 41.287 626.67 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2565}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(626.94*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2565) [list 41.287 626.94 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2651}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(41.31*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2651) [list 41.335 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2645}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(41.418*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2645) [list 41.394 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2553}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.282*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2553) [list 42.301 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2547}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.282*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2547) [list 42.301 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2539}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2539) [list 42.386 723.33 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2533}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2533) [list 42.386 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2527}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2527) [list 42.386 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2521}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2521) [list 42.386 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2515}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2515) [list 42.386 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2509}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2509) [list 42.386 721.98 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2503}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2503) [list 42.386 721.71 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2497}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2497) [list 42.386 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2485}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2485) [list 42.386 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2479}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2479) [list 42.386 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2473}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2473) [list 42.386 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2467}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2467) [list 42.386 720.36 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2461}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.39*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2461) [list 42.386 720.09 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2639}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.444*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2639) [list 42.458 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2633}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.552*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2633) [list 42.549 31.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2621}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.66*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2621) [list 42.64 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2615}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.714*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2615) [list 42.7 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2603}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(42.876*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2603) [list 42.88 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2609}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(42.984*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2609) [list 42.967 30.78 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2597}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(43.038*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2597) [list 43.056 30.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2585}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(43.092*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2585) [list 43.118 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2591}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(43.146*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2591) [list 43.145 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2579}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(43.254*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2579) [list 43.238 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2573}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(43.308*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2573) [list 43.298 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2567}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(43.362*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2567) [list 43.388 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2541}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2541) [list 43.448 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2535}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2535) [list 43.448 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2529}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2529) [list 43.448 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2523}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2523) [list 43.448 625.05 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2517}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2517) [list 43.448 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2511}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2511) [list 43.448 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2505}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2505) [list 43.448 625.86 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2499}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2499) [list 43.448 626.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2487}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2487) [list 43.448 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2481}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(43.47*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2481) [list 43.448 626.67 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2555}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.442*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2555) [list 44.436 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2475}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.442*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2475) [list 44.463 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2469}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.442*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2469) [list 44.463 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2463}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.442*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2463) [list 44.463 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2549}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2549) [list 44.528 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2455}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2455) [list 44.546 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2449}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2449) [list 44.546 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2443}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2443) [list 44.546 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2437}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2437) [list 44.546 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2431}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2431) [list 44.546 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2413}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2413) [list 44.546 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2407}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2407) [list 44.546 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2401}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2401) [list 44.546 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2395}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2395) [list 44.546 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2389}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2389) [list 44.546 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2383}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2383) [list 44.546 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2377}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2377) [list 44.546 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2371}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.55*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2371) [list 44.546 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2543}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.604*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2543) [list 44.588 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2537}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.712*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2537) [list 44.709 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2531}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.766*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2531) [list 44.77 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2525}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.874*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2525) [list 44.861 30.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2519}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(44.928*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2519) [list 44.946 30.51 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2513}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(44.982*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2513) [list 45.005 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2507}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(45.144*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2507) [list 45.125 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2501}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(45.198*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2501) [list 45.185 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2489}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(45.252*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2489) [list 45.245 31.59 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2483}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(45.36*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2483) [list 45.364 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2457}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2457) [list 45.609 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2451}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2451) [list 45.609 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2445}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2445) [list 45.609 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2439}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2439) [list 45.609 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2433}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2433) [list 45.609 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2415}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2415) [list 45.609 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2409}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2409) [list 45.609 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2403}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2403) [list 45.609 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2397}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(45.63*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2397) [list 45.609 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2477}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.494*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2477) [list 46.505 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2471}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.548*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2471) [list 46.566 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2391}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.602*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2391) [list 46.625 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2385}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.602*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2385) [list 46.625 624.51 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2379}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.602*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2379) [list 46.625 624.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2373}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.602*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2373) [list 46.625 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2465}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2465) [list 46.687 31.59 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2365}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2365) [list 46.706 723.33 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2359}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2359) [list 46.706 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2347}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2347) [list 46.706 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2341}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2341) [list 46.706 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2335}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2335) [list 46.706 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2329}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2329) [list 46.706 721.98 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2323}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2323) [list 46.706 721.71 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2317}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2317) [list 46.706 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2311}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2311) [list 46.706 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2305}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2305) [list 46.706 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2299}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2299) [list 46.706 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2293}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2293) [list 46.706 720.36 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2281}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.71*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2281) [list 46.706 720.09 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2459}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.764*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2459) [list 46.748 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2453}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.818*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2453) [list 46.808 31.05 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2447}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(46.818*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2447) [list 46.839 30.78 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2441}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(46.926*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2441) [list 46.928 30.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2435}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(47.088*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2435) [list 47.105 30.24 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2417}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(47.142*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2417) [list 47.165 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2405}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(47.25*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2405) [list 47.251 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2411}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(47.304*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2411) [list 47.284 29.97 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2367}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(47.79*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2367) [list 47.771 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2361}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(47.79*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2361) [list 47.771 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2349}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(47.79*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2349) [list 47.771 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2343}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(47.79*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2343) [list 47.771 625.05 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2337}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(47.79*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2337) [list 47.771 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2331}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(47.79*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2331) [list 47.771 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2325}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(47.79*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2325) [list 47.771 625.86 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2319}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(47.79*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2319) [list 47.771 626.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2399}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(47.844*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2399) [list 47.843 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2313}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.762*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2313) [list 48.787 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2307}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.762*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2307) [list 48.787 624.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2301}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.762*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2301) [list 48.787 624.78 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2295}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.762*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2295) [list 48.787 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2283}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.762*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2283) [list 48.787 625.32 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2275}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2275) [list 48.866 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2269}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2269) [list 48.866 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2263}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2263) [list 48.866 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2257}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2257) [list 48.866 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2251}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2251) [list 48.866 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2245}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2245) [list 48.866 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2239}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2239) [list 48.866 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2233}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2233) [list 48.866 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2227}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2227) [list 48.866 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2215}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2215) [list 48.866 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2209}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2209) [list 48.866 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2203}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2203) [list 48.866 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2197}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.87*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2197) [list 48.866 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2387}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(48.924*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2387) [list 48.908 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2393}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(48.924*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2393) [list 48.939 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2381}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.032*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2381) [list 49.029 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2375}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(49.14*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2375) [list 49.15 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2369}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.248*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2369) [list 49.241 31.05 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2363}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(49.302*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2363) [list 49.328 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2351}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.41*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2351) [list 49.415 30.51 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2345}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(49.518*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2345) [list 49.505 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2339}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.572*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2339) [list 49.566 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2333}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(49.626*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2333) [list 49.625 31.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2321}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.734*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2321) [list 49.737 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2327}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.734*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2327) [list 49.745 29.97 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2277}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(49.95*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2277) [list 49.932 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2271}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.95*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2271) [list 49.932 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2265}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(49.95*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2265) [list 49.932 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2259}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.95*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2259) [list 49.932 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2253}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(49.95*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2253) [list 49.932 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2247}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(49.95*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2247) [list 49.932 625.59 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2241}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(49.95*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2241) [list 49.932 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2315}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(50.868*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2315) [list 50.886 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2235}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(50.922*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2235) [list 50.948 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2229}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(50.922*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2229) [list 50.948 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2217}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(50.922*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2217) [list 50.948 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2211}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(50.922*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2211) [list 50.948 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2205}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(50.922*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2205) [list 50.948 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2199}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(50.922*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2199) [list 50.948 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2309}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(50.976*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2309) [list 50.976 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2191}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2191) [list 51.026 723.33 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2185}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2185) [list 51.026 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2179}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2179) [list 51.026 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2173}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2173) [list 51.026 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2167}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2167) [list 51.026 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2161}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2161) [list 51.026 721.98 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2149}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2149) [list 51.026 721.71 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2143}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2143) [list 51.026 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2137}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2137) [list 51.026 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2131}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2131) [list 51.026 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2125}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2125) [list 51.026 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2119}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2119) [list 51.026 720.36 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2113}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.03*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2113) [list 51.026 720.09 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2303}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.084*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2303) [list 51.067 31.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2297}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.138*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2297) [list 51.128 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2285}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.192*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2285) [list 51.188 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2279}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.3*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2279) [list 51.309 30.78 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2267}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.462*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2267) [list 51.459 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2273}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.462*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2273) [list 51.487 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2261}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.57*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2261) [list 51.549 32.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2255}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.624*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2255) [list 51.639 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2249}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(51.732*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2249) [list 51.72 31.59 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2243}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(51.786*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2243) [list 51.809 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2193}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(52.11*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2193) [list 52.093 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2187}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(52.11*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2187) [list 52.093 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2181}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(52.11*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2181) [list 52.093 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2175}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(52.11*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2175) [list 52.093 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2169}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(52.11*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2169) [list 52.093 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2163}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(52.11*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2163) [list 52.093 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2237}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(52.812*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2237) [list 52.833 32.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2231}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(52.92*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2231) [list 52.925 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2219}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.028*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2219) [list 53.046 31.59 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2213}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.082*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2213) [list 53.076 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2151}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.136*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2151) [list 53.11 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2145}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.136*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2145) [list 53.11 624.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2139}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.136*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2139) [list 53.11 624.78 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2133}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.136*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2133) [list 53.11 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2127}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.136*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2127) [list 53.11 625.32 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2121}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.136*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2121) [list 53.11 625.59 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2115}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.136*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2115) [list 53.11 625.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2107}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2107) [list 53.186 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2101}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2101) [list 53.186 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2095}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2095) [list 53.186 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2083}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2083) [list 53.186 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2077}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2077) [list 53.186 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2071}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2071) [list 53.186 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2065}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2065) [list 53.186 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2059}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2059) [list 53.186 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2053}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2053) [list 53.186 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2047}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2047) [list 53.186 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2041}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2041) [list 53.186 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2035}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2035) [list 53.186 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2029}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2029) [list 53.186 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2207}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.19*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2207) [list 53.198 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2201}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.244*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2201) [list 53.258 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2195}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.352*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2195) [list 53.379 30.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2189}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.46*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2189) [list 53.435 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2183}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.514*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2183) [list 53.495 30.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2177}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.622*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2177) [list 53.645 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2171}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(53.676*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2171) [list 53.675 31.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2165}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(53.784*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2165) [list 53.764 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2109}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(54.27*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2109) [list 54.254 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2103}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(54.27*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2103) [list 54.254 624.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2097}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(54.27*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2097) [list 54.254 624.78 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2085}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(54.27*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2085) [list 54.254 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2079}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(54.27*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2079) [list 54.254 625.32 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2153}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(54.81*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2153) [list 54.811 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2147}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(54.918*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2147) [list 54.902 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2141}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(54.918*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2141) [list 54.902 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2135}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.08*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2135) [list 55.085 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2129}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.242*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2129) [list 55.236 31.05 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2123}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.242*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2123) [list 55.265 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2073}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.296*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2073) [list 55.272 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2067}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.296*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2067) [list 55.272 624.51 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2061}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.296*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2061) [list 55.272 624.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2055}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.296*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2055) [list 55.272 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2049}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.296*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2049) [list 55.272 625.32 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2043}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.296*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2043) [list 55.272 625.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2037}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.296*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2037) [list 55.272 625.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2031}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.296*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2031) [list 55.272 626.13 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2117}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2117) [list 55.325 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2017}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2017) [list 55.346 723.33 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire2011}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2011) [list 55.346 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2005}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2005) [list 55.346 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1999}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1999) [list 55.346 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1993}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1993) [list 55.346 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1987}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1987) [list 55.346 721.98 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1981}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1981) [list 55.346 721.71 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1975}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1975) [list 55.346 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1969}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1969) [list 55.346 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1963}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1963) [list 55.346 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1951}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1951) [list 55.346 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1945}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(720.36*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1945) [list 55.346 720.36 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1939}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.35*$ot_gap_dbu)}] [expr {round(720.09*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1939) [list 55.346 720.09 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2111}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.403999999999996*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2111) [list 55.386 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2105}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.512*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2105) [list 55.507 32.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2099}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.566*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2099) [list 55.567 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2087}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(55.674*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2087) [list 55.657 31.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2081}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(55.836*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2081) [list 55.861 31.32 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2019}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(56.43*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2019) [list 56.415 624.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2013}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(56.43*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2013) [list 56.415 624.51 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire2007}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(56.43*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2007) [list 56.415 624.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2001}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(56.43*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2001) [list 56.415 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2075}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(56.808*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2075) [list 56.788 32.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2069}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(56.862*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2069) [list 56.881 31.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1995}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1995) [list 57.434 624.24 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1989}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1989) [list 57.434 624.51 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1983}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1983) [list 57.434 624.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1977}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1977) [list 57.434 625.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1971}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1971) [list 57.434 625.32 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1965}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1965) [list 57.434 625.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1953}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1953) [list 57.434 625.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1947}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1947) [list 57.434 626.13 0.6480000000000032 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1941}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.456*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1941) [list 57.434 626.4 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2063}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2063) [list 57.486 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1933}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1933) [list 57.506 723.33 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1927}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1927) [list 57.506 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1921}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1921) [list 57.506 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1915}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1915) [list 57.506 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1909}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1909) [list 57.506 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1903}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1903) [list 57.506 721.98 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1897}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1897) [list 57.506 721.71 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1885}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1885) [list 57.506 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1879}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1879) [list 57.506 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1873}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1873) [list 57.506 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1867}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.51*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1867) [list 57.506 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2057}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.564*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2057) [list 57.579 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2051}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.672*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2051) [list 57.669 31.59 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2045}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.726*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2045) [list 57.726 31.32 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2039}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(57.834*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2039) [list 57.846 31.05 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2033}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(57.942*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2033) [list 57.936 30.78 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2021}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(58.05*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2021) [list 58.026 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2015}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(58.104*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2015) [list 58.086 30.24 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire2009}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(58.211999999999996*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2009) [list 58.206 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire2003}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(58.266*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire2003) [list 58.266 31.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1935}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(58.589999999999996*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1935) [list 58.575 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1929}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(58.589999999999996*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1929) [list 58.575 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1923}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(58.589999999999996*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1923) [list 58.575 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1997}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.346*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1997) [list 59.344 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1991}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.4*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1991) [list 59.405 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1985}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.508*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1985) [list 59.496 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1979}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.562*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1979) [list 59.586 31.32 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1917}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.616*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1917) [list 59.594 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1911}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.616*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1911) [list 59.594 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1905}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.616*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1905) [list 59.594 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1899}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.616*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1899) [list 59.594 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1887}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.616*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1887) [list 59.594 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1881}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.616*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1881) [list 59.594 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1875}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.616*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1875) [list 59.594 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1869}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.616*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1869) [list 59.594 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1973}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1973) [list 59.647 31.05 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1861}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1861) [list 59.666 723.33 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1855}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1855) [list 59.666 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1849}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1849) [list 59.666 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1843}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1843) [list 59.666 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1837}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1837) [list 59.666 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1831}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1831) [list 59.666 721.98 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1819}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1819) [list 59.666 721.71 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1813}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1813) [list 59.666 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1807}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1807) [list 59.666 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1801}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1801) [list 59.666 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1795}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.67*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1795) [list 59.666 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1967}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.724*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1967) [list 59.738 30.78 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1955}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.832*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1955) [list 59.829 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1949}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(59.94*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1949) [list 59.92 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1943}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(59.994*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1943) [list 60.004 32.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1937}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(60.102*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1937) [list 60.097 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1931}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(60.21*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1931) [list 60.185 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1925}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(60.264*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1925) [list 60.271 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1863}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(60.75*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1863) [list 60.734 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1857}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(60.75*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1857) [list 60.734 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1851}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(60.75*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1851) [list 60.734 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1845}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(60.75*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1845) [list 60.734 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1919}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.29*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1919) [list 61.291 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1913}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.344*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1913) [list 61.352 31.86 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1907}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.452*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1907) [list 61.474 31.59 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1901}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.56*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1901) [list 61.534 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1889}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.668*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1889) [list 61.656 31.05 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1883}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.722*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1883) [list 61.717 30.78 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1839}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.775999999999996*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1839) [list 61.752 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1833}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.775999999999996*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1833) [list 61.752 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1821}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.775999999999996*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1821) [list 61.752 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1815}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.775999999999996*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1815) [list 61.752 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1809}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.775999999999996*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1809) [list 61.752 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1803}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.775999999999996*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1803) [list 61.752 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1797}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.775999999999996*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1797) [list 61.752 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1877}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1877) [list 61.808 30.51 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1789}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1789) [list 61.826 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1783}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1783) [list 61.826 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1777}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1777) [list 61.826 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1771}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1771) [list 61.826 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1765}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1765) [list 61.826 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1747}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1747) [list 61.826 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1741}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1741) [list 61.826 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1735}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1735) [list 61.826 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1729}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1729) [list 61.826 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1723}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1723) [list 61.826 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1717}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.83*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1717) [list 61.826 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1871}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(61.884*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1871) [list 61.895 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1865}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(61.992*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1865) [list 61.985 32.13 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1859}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(62.046*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1859) [list 62.045 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1853}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(62.153999999999996*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1853) [list 62.134 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1847}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(62.208*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1847) [list 62.224 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1791}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(62.91*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1791) [list 62.893 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1785}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(62.91*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1785) [list 62.893 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1779}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(62.91*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1779) [list 62.893 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1773}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(62.91*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1773) [list 62.893 625.05 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1767}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(62.91*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1767) [list 62.893 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1841}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.234*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1841) [list 63.238 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1835}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.342*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1835) [list 63.359 31.86 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1823}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.396*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1823) [list 63.42 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1811}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.612*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1811) [list 63.603 31.32 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1805}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.666*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1805) [list 63.664 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1817}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.72*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1817) [list 63.694 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1799}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.774*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1799) [list 63.785 30.51 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1793}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.828*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1793) [list 63.845 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1749}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.936*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1749) [list 63.91 624.24 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1743}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.936*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1743) [list 63.91 624.51 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1737}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.936*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1737) [list 63.91 624.78 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1731}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.936*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1731) [list 63.91 625.05 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1725}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.936*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1725) [list 63.91 625.32 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1719}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.936*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1719) [list 63.91 625.59 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1787}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1787) [list 63.966 32.13 0.6480000000000032 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1711}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1711) [list 63.986 723.33 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1705}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1705) [list 63.986 723.06 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1699}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1699) [list 63.986 722.79 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1693}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1693) [list 63.986 722.52 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1681}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1681) [list 63.986 722.25 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1675}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1675) [list 63.986 721.98 0.6480000000000032 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1669}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1669) [list 63.986 721.71 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1663}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1663) [list 63.986 721.44 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1657}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1657) [list 63.986 721.17 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1651}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1651) [list 63.986 720.9 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1645}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(63.99*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1645) [list 63.986 720.63 0.6480000000000032 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1781}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(64.206*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1781) [list 64.204 31.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1775}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(64.25999999999999*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1775) [list 64.264 31.59 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1769}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(64.314*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1769) [list 64.294 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1713}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(65.07*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1713) [list 65.052 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1707}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(65.07*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1707) [list 65.052 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1701}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(65.07*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1701) [list 65.052 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1695}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(65.07*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1695) [list 65.052 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1683}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(65.07*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1683) [list 65.052 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1677}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(65.07*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1677) [list 65.052 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1745}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(65.286*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1745) [list 65.306 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1751}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(65.34*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1751) [list 65.337 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1739}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(65.394*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1739) [list 65.398 31.59 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1733}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(65.50200000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1733) [list 65.491 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1671}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.042*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1671) [list 66.068 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1665}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.042*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1665) [list 66.068 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1659}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.042*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1659) [list 66.068 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1653}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.042*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1653) [list 66.068 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1647}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.042*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1647) [list 66.068 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1727}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.096*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1727) [list 66.095 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1639}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1639) [list 66.146 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1633}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1633) [list 66.146 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1627}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1627) [list 66.146 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1615}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1615) [list 66.146 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1609}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1609) [list 66.146 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1603}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1603) [list 66.146 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1597}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1597) [list 66.146 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1591}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1591) [list 66.146 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1585}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1585) [list 66.146 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1579}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1579) [list 66.146 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1573}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.15*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1573) [list 66.146 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1721}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.20400000000001*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1721) [list 66.186 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1715}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.25800000000001*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1715) [list 66.276 31.59 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1709}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.312*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1709) [list 66.337 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1703}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.42*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1703) [list 66.427 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1697}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.52799999999999*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1697) [list 66.518 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1685}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(66.582*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1685) [list 66.605 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1679}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(66.69*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1679) [list 66.691 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1641}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(67.22999999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1641) [list 67.211 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1635}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(67.22999999999999*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1635) [list 67.211 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1629}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(67.22999999999999*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1629) [list 67.211 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1617}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(67.22999999999999*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1617) [list 67.211 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1611}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(67.22999999999999*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1611) [list 67.211 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1605}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(67.22999999999999*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1605) [list 67.211 625.59 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1599}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(67.22999999999999*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1599) [list 67.211 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1673}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(67.71600000000001*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1673) [list 67.741 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1667}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(67.824*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1667) [list 67.832 31.86 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1661}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(67.878*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1661) [list 67.893 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1655}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(67.98599999999999*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1655) [list 67.984 31.32 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1649}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.148*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1649) [list 68.166 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1643}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.148*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1643) [list 68.166 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1637}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.202*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1637) [list 68.227 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1593}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.202*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1593) [list 68.227 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1587}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.202*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1587) [list 68.227 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1581}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.202*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1581) [list 68.227 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1575}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.202*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1575) [list 68.227 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1567}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1567) [list 68.306 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1561}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1561) [list 68.306 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1549}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1549) [list 68.306 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1543}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1543) [list 68.306 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1537}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1537) [list 68.306 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1531}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1531) [list 68.306 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1525}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1525) [list 68.306 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1519}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1519) [list 68.306 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1513}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1513) [list 68.306 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1507}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1507) [list 68.306 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1501}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.31*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1501) [list 68.306 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1631}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.364*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1631) [list 68.348 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1619}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.418*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1619) [list 68.404 30.24 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1613}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.52600000000001*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1613) [list 68.527 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1607}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(68.58000000000001*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1607) [list 68.583 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1601}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(68.63399999999999*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1601) [list 68.643 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1569}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(69.38999999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1569) [list 69.369 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1563}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(69.38999999999999*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1563) [list 69.369 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1551}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(69.38999999999999*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1551) [list 69.369 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1545}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(69.38999999999999*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1545) [list 69.369 625.05 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1539}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(69.38999999999999*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1539) [list 69.369 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1533}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(69.38999999999999*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1533) [list 69.369 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1527}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(69.38999999999999*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1527) [list 69.369 625.86 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1521}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(69.38999999999999*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1521) [list 69.369 626.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1595}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(69.714*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1595) [list 69.718 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1589}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(69.768*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1589) [list 69.779 31.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1583}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(69.876*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1583) [list 69.87 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1577}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(69.98400000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1577) [list 69.961 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1571}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.14599999999999*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1571) [list 70.144 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1565}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.19999999999999*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1565) [list 70.204 30.78 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1553}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.30799999999999*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1553) [list 70.325 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1547}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.362*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1547) [list 70.385 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1515}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.362*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1515) [list 70.385 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1509}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.362*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1509) [list 70.385 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1503}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.362*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1503) [list 70.385 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1541}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.362*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1541) [list 70.386 30.24 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1495}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1495) [list 70.466 723.33 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1483}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1483) [list 70.466 723.06 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1477}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1477) [list 70.466 722.79 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1471}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1471) [list 70.466 722.52 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1465}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1465) [list 70.466 722.25 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1459}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1459) [list 70.466 721.98 0.6480000000000103 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1453}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1453) [list 70.466 721.71 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1447}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1447) [list 70.466 721.44 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1441}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1441) [list 70.466 721.17 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1435}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1435) [list 70.466 720.9 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1429}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1429) [list 70.466 720.63 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1535}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.47*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1535) [list 70.476 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1529}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(70.578*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1529) [list 70.566 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1523}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(70.74000000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1523) [list 70.743 31.32 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1497}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1497) [list 71.528 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1485}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1485) [list 71.528 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1479}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1479) [list 71.528 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1473}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1473) [list 71.528 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1467}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1467) [list 71.528 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1461}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1461) [list 71.528 625.59 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1455}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1455) [list 71.528 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1449}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1449) [list 71.528 626.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1443}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(71.55000000000001*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1443) [list 71.528 626.4 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1517}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(71.76599999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1517) [list 71.758 32.13 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1505}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(71.82*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1505) [list 71.847 31.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1511}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(71.874*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1511) [list 71.879 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1499}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(71.928*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1499) [list 71.939 31.32 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1487}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.036*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1487) [list 72.031 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1481}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.144*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1481) [list 72.122 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1475}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.19800000000001*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1475) [list 72.182 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1469}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.25200000000001*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1469) [list 72.274 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1463}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.36000000000001*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1463) [list 72.364 29.97 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1457}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.41399999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1457) [list 72.424 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1437}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.52199999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1437) [list 72.543 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1431}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.52199999999999*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1431) [list 72.543 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1451}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.52199999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1451) [list 72.544 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1445}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1445) [list 72.604 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1417}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1417) [list 72.626 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1411}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1411) [list 72.626 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1405}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1405) [list 72.626 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1399}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1399) [list 72.626 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1393}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1393) [list 72.626 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1387}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1387) [list 72.626 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1381}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1381) [list 72.626 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1375}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1375) [list 72.626 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1369}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1369) [list 72.626 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1363}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1363) [list 72.626 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1351}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(72.63*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1351) [list 72.626 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1439}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(73.602*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1439) [list 73.615 32.13 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1419}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1419) [list 73.687 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1413}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1413) [list 73.687 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1407}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1407) [list 73.687 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1401}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1401) [list 73.687 625.05 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1395}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1395) [list 73.687 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1389}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1389) [list 73.687 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1383}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1383) [list 73.687 625.86 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1377}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1377) [list 73.687 626.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1371}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1371) [list 73.687 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1365}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1365) [list 73.687 626.67 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1433}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(73.71000000000001*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1433) [list 73.735 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1421}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(73.81800000000001*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1421) [list 73.795 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1415}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(73.92599999999999*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1415) [list 73.918 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1403}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.03399999999999*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1403) [list 74.039 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1409}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(74.088*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1409) [list 74.101 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1397}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.142*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1397) [list 74.162 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1353}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(74.68199999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1353) [list 74.701 624.24 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1391}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1391) [list 74.764 32.13 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1345}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1345) [list 74.786 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1339}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1339) [list 74.786 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1333}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1333) [list 74.786 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1327}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1327) [list 74.786 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1321}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1321) [list 74.786 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1315}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1315) [list 74.786 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1309}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1309) [list 74.786 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1303}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1303) [list 74.786 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1297}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1297) [list 74.786 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1285}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1285) [list 74.786 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1279}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.78999999999999*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1279) [list 74.786 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1385}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(74.844*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1385) [list 74.856 31.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1379}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(74.898*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1379) [list 74.916 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1373}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(75.006*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1373) [list 75.006 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1367}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(75.06*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1367) [list 75.033 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1347}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1347) [list 75.846 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1341}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1341) [list 75.846 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1335}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1335) [list 75.846 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1329}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1329) [list 75.846 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1323}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1323) [list 75.846 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1317}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1317) [list 75.846 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1311}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1311) [list 75.846 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1305}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1305) [list 75.846 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1299}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1299) [list 75.846 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1287}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1287) [list 75.846 626.67 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1281}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(75.87*$ot_gap_dbu)}] [expr {round(626.94*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1281) [list 75.846 626.94 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1355}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.03200000000001*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1355) [list 76.047 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1349}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.24799999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1349) [list 76.228 31.86 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1343}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.30199999999999*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1343) [list 76.321 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1337}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.41*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1337) [list 76.411 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1331}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.464*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1331) [list 76.472 31.05 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1325}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.572*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1325) [list 76.593 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1319}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.68*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1319) [list 76.654 32.13 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1313}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.73400000000001*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1313) [list 76.715 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1307}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.84200000000001*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1307) [list 76.836 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1301}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.89599999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1301) [list 76.895 31.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1273}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1273) [list 76.946 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1267}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1267) [list 76.946 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1261}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1261) [list 76.946 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1255}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1255) [list 76.946 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1249}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1249) [list 76.946 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1243}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1243) [list 76.946 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1237}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1237) [list 76.946 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1231}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1231) [list 76.946 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1219}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1219) [list 76.946 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1213}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1213) [list 76.946 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1207}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(76.94999999999999*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1207) [list 76.946 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1289}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(77.00399999999999*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1289) [list 77.013 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1283}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(77.05799999999999*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1283) [list 77.075 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1275}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1275) [list 78.005 624.24 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1269}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1269) [list 78.005 624.51 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1263}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1263) [list 78.005 624.78 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1257}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1257) [list 78.005 625.05 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1251}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1251) [list 78.005 625.32 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1245}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1245) [list 78.005 625.59 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1239}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1239) [list 78.005 625.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1233}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1233) [list 78.005 626.13 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1221}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1221) [list 78.005 626.4 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1215}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1215) [list 78.005 626.67 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1209}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.03*$ot_gap_dbu)}] [expr {round(626.94*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1209) [list 78.005 626.94 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1277}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.138*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1277) [list 78.114 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1271}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.24600000000001*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1271) [list 78.267 31.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1265}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.30000000000001*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1265) [list 78.299 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1259}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.35400000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1259) [list 78.36 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1253}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.46199999999999*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1253) [list 78.45 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1247}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.51599999999999*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1247) [list 78.541 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1241}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.624*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1241) [list 78.632 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1223}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.786*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1223) [list 78.784 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1235}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.894*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1235) [list 78.904 31.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10345}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(78.894*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10345) [list 78.91 624.24 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1217}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(78.94800000000001*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1217) [list 78.964 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire10392}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(79.00200000000001*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10392) [list 79.016 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1205}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(79.00200000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1205) [list 79.025 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1211}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(79.05600000000001*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1211) [list 79.054 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1201}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1201) [list 79.106 723.33 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1195}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1195) [list 79.106 723.06 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1189}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1189) [list 79.106 722.79 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1183}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1183) [list 79.106 722.52 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1177}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1177) [list 79.106 722.25 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1171}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1171) [list 79.106 721.98 0.6480000000000103 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1165}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1165) [list 79.106 721.71 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1153}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1153) [list 79.106 721.44 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1147}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1147) [list 79.106 721.17 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1141}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1141) [list 79.106 720.9 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1135}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1135) [list 79.106 720.63 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1203}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(79.11000000000001*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1203) [list 79.121 624.78 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1199}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.082*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1199) [list 80.094 32.13 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1197}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1197) [list 80.164 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1191}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1191) [list 80.164 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1185}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1185) [list 80.164 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1179}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1179) [list 80.164 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1173}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1173) [list 80.164 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1167}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1167) [list 80.164 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1155}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1155) [list 80.164 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1149}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1149) [list 80.164 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1143}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1143) [list 80.164 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1137}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1137) [list 80.164 626.67 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1193}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.19*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1193) [list 80.185 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1187}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.244*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1187) [list 80.244 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1181}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.352*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1181) [list 80.336 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1175}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.406*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1175) [list 80.427 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1169}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.51400000000001*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1169) [list 80.521 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1157}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.62199999999999*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1157) [list 80.611 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1151}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.67599999999999*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1151) [list 80.672 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1145}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.78399999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1145) [list 80.762 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1139}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(80.838*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1139) [list 80.853 31.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1133}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(80.892*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1133) [list 80.913 31.59 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1127}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(81.054*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1127) [list 81.034 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1129}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1129) [list 81.266 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1123}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1123) [list 81.266 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1117}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1117) [list 81.266 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1111}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1111) [list 81.266 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1105}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1105) [list 81.266 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1099}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1099) [list 81.266 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1081}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1081) [list 81.266 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1075}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1075) [list 81.266 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1069}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1069) [list 81.266 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1063}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1063) [list 81.266 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1057}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1057) [list 81.266 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1131}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1131) [list 81.281 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1125}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(81.27000000000001*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1125) [list 81.281 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1121}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.18799999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1121) [list 82.166 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1115}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.24199999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1115) [list 82.226 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1103}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1103) [list 82.284 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1109}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1109) [list 82.317 31.32 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1119}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1119) [list 82.323 624.24 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1113}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1113) [list 82.323 624.51 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1107}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1107) [list 82.323 624.78 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1101}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1101) [list 82.323 625.05 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1083}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1083) [list 82.323 625.32 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1077}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1077) [list 82.323 625.59 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1071}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1071) [list 82.323 625.86 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1065}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1065) [list 82.323 626.13 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1059}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.29599999999999*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1059) [list 82.323 626.4 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1085}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.404*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1085) [list 82.408 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1079}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.458*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1079) [list 82.468 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1073}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.566*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1073) [list 82.589 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1067}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(82.78200000000001*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1067) [list 82.772 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1055}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.78200000000001*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1055) [list 82.802 29.97 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1061}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(82.83600000000001*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1061) [list 82.832 32.13 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1051}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1051) [list 83.426 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1045}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1045) [list 83.426 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1039}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1039) [list 83.426 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1033}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1033) [list 83.426 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1027}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1027) [list 83.426 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1015}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1015) [list 83.426 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire1009}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1009) [list 83.426 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1003}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1003) [list 83.426 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire997}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire997) [list 83.426 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire991}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire991) [list 83.426 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire985}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire985) [list 83.426 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1049}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1049) [list 83.433 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1053}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1053) [list 83.441 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1047}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1047) [list 83.441 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1041}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(83.43*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1041) [list 83.441 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1043}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(83.53800000000001*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1043) [list 83.524 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1035}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(84.45599999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1035) [list 84.482 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1029}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(84.45599999999999*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1029) [list 84.482 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire1017}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(84.45599999999999*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1017) [list 84.482 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1011}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(84.45599999999999*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1011) [list 84.482 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1005}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(84.45599999999999*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1005) [list 84.482 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire999}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(84.45599999999999*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire999) [list 84.482 625.59 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire993}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(84.45599999999999*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire993) [list 84.482 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire987}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(84.45599999999999*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire987) [list 84.482 626.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1037}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(84.50999999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1037) [list 84.535 32.13 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1031}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(84.618*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1031) [list 84.626 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1019}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(84.726*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1019) [list 84.717 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire1013}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(84.834*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1013) [list 84.838 31.32 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1007}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(84.888*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1007) [list 84.901 31.05 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire1001}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(84.94200000000001*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire1001) [list 84.961 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire995}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.10400000000001*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire995) [list 85.082 30.51 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire989}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.15799999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire989) [list 85.142 32.13 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire983}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.21199999999999*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire983) [list 85.233 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire977}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.32*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire977) [list 85.324 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire971}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.482*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire971) [list 85.504 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire965}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire965) [list 85.564 31.32 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire979}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire979) [list 85.586 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire973}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire973) [list 85.586 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire967}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire967) [list 85.586 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire961}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire961) [list 85.586 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire949}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire949) [list 85.586 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire943}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire943) [list 85.586 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire937}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire937) [list 85.586 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire931}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire931) [list 85.586 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire925}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire925) [list 85.586 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire919}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire919) [list 85.586 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire913}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire913) [list 85.586 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire981}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire981) [list 85.6 624.24 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire975}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire975) [list 85.6 624.51 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire969}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire969) [list 85.6 624.78 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire963}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(85.59*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire963) [list 85.6 625.05 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire947}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire947) [list 86.603 32.13 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire953}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire953) [list 86.635 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire951}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire951) [list 86.641 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire945}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire945) [list 86.641 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire939}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire939) [list 86.641 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire933}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire933) [list 86.641 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire927}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire927) [list 86.641 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire921}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire921) [list 86.641 625.59 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire915}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(86.61599999999999*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire915) [list 86.641 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire935}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(86.77799999999999*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire935) [list 86.785 31.59 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire941}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(86.77799999999999*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire941) [list 86.786 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire929}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(86.886*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire929) [list 86.878 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire923}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(86.94*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire923) [list 86.937 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire917}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.048*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire917) [list 87.031 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire911}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.156*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire911) [list 87.151 30.24 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire905}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.21000000000001*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire905) [list 87.212 29.97 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire899}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.26400000000001*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire899) [list 87.272 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire887}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.37199999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire887) [list 87.393 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire881}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.47999999999999*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire881) [list 87.454 31.59 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire907}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire907) [list 87.746 723.33 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire901}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire901) [list 87.746 723.06 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire895}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire895) [list 87.746 722.79 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire883}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire883) [list 87.746 722.52 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire877}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire877) [list 87.746 722.25 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire871}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire871) [list 87.746 721.98 0.6480000000000103 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire865}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire865) [list 87.746 721.71 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire859}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire859) [list 87.746 721.44 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire853}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire853) [list 87.746 721.17 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire847}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire847) [list 87.746 720.9 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire841}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire841) [list 87.746 720.63 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire909}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire909) [list 87.76 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire903}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire903) [list 87.76 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire897}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire897) [list 87.76 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire885}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire885) [list 87.76 625.05 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire879}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(87.75*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire879) [list 87.76 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire875}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(88.506*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire875) [list 88.488 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire863}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(88.668*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire863) [list 88.671 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire869}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(88.72200000000001*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire869) [list 88.705 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire857}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(88.72200000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire857) [list 88.739 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire873}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(88.77600000000001*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire873) [list 88.8 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire867}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(88.77600000000001*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire867) [list 88.8 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire861}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(88.77600000000001*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire861) [list 88.8 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire855}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(88.77600000000001*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire855) [list 88.8 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire849}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(88.77600000000001*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire849) [list 88.8 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire843}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(88.77600000000001*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire843) [list 88.8 625.59 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire851}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(88.83000000000001*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire851) [list 88.856 31.05 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire845}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(88.93799999999999*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire845) [list 88.917 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire839}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(88.99199999999999*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire839) [list 89.007 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire833}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.1*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire833) [list 89.101 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire821}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.154*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire821) [list 89.161 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire815}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.262*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire815) [list 89.282 29.97 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire809}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.316*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire809) [list 89.342 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire803}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.424*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire803) [list 89.402 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire835}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire835) [list 89.906 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire829}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire829) [list 89.906 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire817}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire817) [list 89.906 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire811}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire811) [list 89.906 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire805}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire805) [list 89.906 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire799}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire799) [list 89.906 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire793}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire793) [list 89.906 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire787}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire787) [list 89.906 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire781}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire781) [list 89.906 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire775}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire775) [list 89.906 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire769}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire769) [list 89.906 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire837}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire837) [list 89.92 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire831}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire831) [list 89.92 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire819}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire819) [list 89.92 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire813}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire813) [list 89.92 625.05 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire807}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire807) [list 89.92 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire801}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(89.91*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire801) [list 89.92 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire797}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(90.44999999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire797) [list 90.47 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire791}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(90.666*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire791) [list 90.656 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire785}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(90.72*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire785) [list 90.717 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire779}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(90.828*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire779) [list 90.837 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire773}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(90.882*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire773) [list 90.897 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire767}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(90.936*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire767) [list 90.957 30.78 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire795}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(90.936*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire795) [list 90.958 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire789}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(90.936*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire789) [list 90.958 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire783}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(90.936*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire783) [list 90.958 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire777}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(90.936*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire777) [list 90.958 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire771}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(90.936*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire771) [list 90.958 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire755}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(90.99000000000001*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire755) [list 90.987 30.51 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire749}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(91.09800000000001*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire749) [list 91.078 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire743}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(91.25999999999999*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire743) [list 91.261 30.24 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire737}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(91.314*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire737) [list 91.321 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire725}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(91.422*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire725) [list 91.413 31.59 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire731}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(91.422*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire731) [list 91.442 29.97 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire763}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire763) [list 92.066 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire751}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire751) [list 92.066 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire745}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire745) [list 92.066 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire739}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire739) [list 92.066 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire733}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire733) [list 92.066 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire727}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire727) [list 92.066 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire721}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire721) [list 92.066 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire715}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire715) [list 92.066 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire709}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire709) [list 92.066 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire703}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire703) [list 92.066 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire697}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire697) [list 92.066 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire765}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire765) [list 92.079 624.24 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire753}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire753) [list 92.079 624.51 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire747}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire747) [list 92.079 624.78 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire741}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire741) [list 92.079 625.05 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire735}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire735) [list 92.079 625.32 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire729}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire729) [list 92.079 625.59 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire723}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(92.07*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire723) [list 92.079 625.86 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire719}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(92.988*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire719) [list 92.967 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire707}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(93.042*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire707) [list 93.057 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire713}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(93.096*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire713) [list 93.085 31.59 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire717}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(93.096*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire717) [list 93.117 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire711}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(93.096*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire711) [list 93.117 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire705}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(93.096*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire705) [list 93.117 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire699}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(93.096*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire699) [list 93.117 625.05 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire701}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(93.20400000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire701) [list 93.206 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire689}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(93.31200000000001*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire689) [list 93.297 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire683}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(93.36599999999999*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire683) [list 93.388 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire677}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(93.47399999999999*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire677) [list 93.48 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire671}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(93.582*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire671) [list 93.572 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire665}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(93.636*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire665) [list 93.662 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire659}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(93.744*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire659) [list 93.722 31.86 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire653}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(93.798*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire653) [list 93.813 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire647}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(93.906*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire647) [list 93.903 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire685}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire685) [list 94.226 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire679}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire679) [list 94.226 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire673}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire673) [list 94.226 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire667}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire667) [list 94.226 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire661}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire661) [list 94.226 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire655}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire655) [list 94.226 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire649}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire649) [list 94.226 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire643}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire643) [list 94.226 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire637}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire637) [list 94.226 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire631}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire631) [list 94.226 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire619}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire619) [list 94.226 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire687}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire687) [list 94.239 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire681}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire681) [list 94.239 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire675}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire675) [list 94.239 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire669}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire669) [list 94.239 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire663}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire663) [list 94.239 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire657}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire657) [list 94.239 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire651}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire651) [list 94.239 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire645}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(94.22999999999999*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire645) [list 94.239 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire641}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(95.03999999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire641) [list 95.034 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire635}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(95.148*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire635) [list 95.127 31.86 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire623}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(95.202*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire623) [list 95.217 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire611}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(95.256*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire611) [list 95.275 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire639}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(95.256*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire639) [list 95.276 624.24 0.6480000000000103 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire633}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(95.256*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire633) [list 95.276 624.51 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire621}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(95.256*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire621) [list 95.276 624.78 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire617}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(95.256*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire617) [list 95.277 31.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire605}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(95.364*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire605) [list 95.368 30.78 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire599}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(95.47200000000001*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire599) [list 95.457 30.51 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire593}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(95.52600000000001*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire593) [list 95.517 30.24 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire587}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(95.63399999999999*$ot_gap_dbu)}] [expr {round(29.97*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire587) [list 95.642 29.97 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire581}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(95.68799999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire581) [list 95.701 32.13 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire575}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(95.79599999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire575) [list 95.791 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire569}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(95.904*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire569) [list 95.882 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire613}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire613) [list 96.386 723.33 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire607}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire607) [list 96.386 723.06 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire601}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire601) [list 96.386 722.79 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire595}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire595) [list 96.386 722.52 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire589}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire589) [list 96.386 722.25 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire583}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire583) [list 96.386 721.98 0.6480000000000103 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire577}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire577) [list 96.386 721.71 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire571}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire571) [list 96.386 721.44 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire565}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire565) [list 96.386 721.17 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire553}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire553) [list 96.386 720.9 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire547}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire547) [list 96.386 720.63 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire615}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire615) [list 96.399 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire609}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire609) [list 96.399 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire603}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire603) [list 96.399 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire597}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire597) [list 96.399 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire591}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire591) [list 96.399 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire585}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire585) [list 96.399 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire579}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire579) [list 96.399 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire573}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire573) [list 96.399 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire567}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.38999999999999*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire567) [list 96.399 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire557}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(96.93*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire557) [list 96.926 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire551}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(96.98400000000001*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire551) [list 96.986 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire545}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(97.09200000000001*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire545) [list 97.076 31.59 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire539}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(97.14599999999999*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire539) [list 97.166 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire533}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(97.19999999999999*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire533) [list 97.226 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire527}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(97.362*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire527) [list 97.346 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire555}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(97.416*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire555) [list 97.435 624.24 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire549}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(97.416*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire549) [list 97.435 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire521}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(97.524*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire521) [list 97.53 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire515}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(97.578*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire515) [list 97.59 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire503}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(97.632*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire503) [list 97.649 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire509}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(97.686*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire509) [list 97.681 30.24 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire491}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(97.79400000000001*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire491) [list 97.77 31.59 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire485}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(97.84800000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire485) [list 97.83 31.32 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire541}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire541) [list 98.546 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire535}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire535) [list 98.546 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire529}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire529) [list 98.546 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire523}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire523) [list 98.546 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire517}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire517) [list 98.546 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire511}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire511) [list 98.546 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire505}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire505) [list 98.546 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire499}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire499) [list 98.546 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire487}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire487) [list 98.546 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire481}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire481) [list 98.546 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire475}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire475) [list 98.546 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire543}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire543) [list 98.558 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire537}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire537) [list 98.558 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire531}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire531) [list 98.558 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire525}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire525) [list 98.558 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire519}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire519) [list 98.558 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire513}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire513) [list 98.558 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire507}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire507) [list 98.558 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire501}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire501) [list 98.558 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire489}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire489) [list 98.558 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire483}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.55000000000001*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire483) [list 98.558 626.67 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire479}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(98.874*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire479) [list 98.9 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire473}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(98.982*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire473) [list 98.956 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire461}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(99.036*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire461) [list 99.06 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire467}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(99.19800000000001*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire467) [list 99.202 31.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire455}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(99.25200000000001*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire455) [list 99.236 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire449}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(99.30600000000001*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire449) [list 99.296 30.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire443}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(99.41399999999999*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire443) [list 99.421 30.51 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire437}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(99.46799999999999*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire437) [list 99.48 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire419}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(99.52199999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire419) [list 99.54 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire477}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(99.576*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire477) [list 99.594 624.24 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire413}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(99.684*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire413) [list 99.659 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire401}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(99.792*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire401) [list 99.81 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire407}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(99.846*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire407) [list 99.841 31.32 0.6480000000000103 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire469}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire469) [list 100.706 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire463}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire463) [list 100.706 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire457}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire457) [list 100.706 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire451}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire451) [list 100.706 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire445}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire445) [list 100.706 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire439}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire439) [list 100.706 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire433}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire433) [list 100.706 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire415}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire415) [list 100.706 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire409}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire409) [list 100.706 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire403}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire403) [list 100.706 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire397}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire397) [list 100.706 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire471}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire471) [list 100.718 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire465}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire465) [list 100.718 624.51 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire459}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire459) [list 100.718 624.78 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire453}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire453) [list 100.718 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire447}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire447) [list 100.718 625.32 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire441}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire441) [list 100.718 625.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire435}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire435) [list 100.718 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire417}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire417) [list 100.718 626.13 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire411}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire411) [list 100.718 626.4 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire405}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire405) [list 100.718 626.67 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire399}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.71000000000001*$ot_gap_dbu)}] [expr {round(626.94*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire399) [list 100.718 626.94 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire389}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(100.92599999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire389) [list 100.912 32.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire395}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(100.97999999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire395) [list 100.976 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire383}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(101.03399999999999*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire383) [list 101.04 31.59 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire377}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(101.62799999999999*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire377) [list 101.634 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire371}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(101.73599999999999*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire371) [list 101.726 31.86 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire365}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(101.844*$ot_gap_dbu)}] [expr {round(31.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire365) [list 101.819 31.59 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire353}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(101.898*$ot_gap_dbu)}] [expr {round(31.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire353) [list 101.88 31.32 0.6480000000000103 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire347}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(101.952*$ot_gap_dbu)}] [expr {round(31.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire347) [list 101.97 31.05 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire341}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.06*$ot_gap_dbu)}] [expr {round(30.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire341) [list 102.06 30.78 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire335}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.168*$ot_gap_dbu)}] [expr {round(30.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire335) [list 102.15 30.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire329}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.22200000000001*$ot_gap_dbu)}] [expr {round(30.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire329) [list 102.212 30.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire391}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire391) [list 102.866 723.33 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire385}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire385) [list 102.866 723.06 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire379}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(722.79*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire379) [list 102.866 722.79 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire373}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(722.52*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire373) [list 102.866 722.52 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire367}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(722.25*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire367) [list 102.866 722.25 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire361}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(721.98*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire361) [list 102.866 721.98 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire349}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(721.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire349) [list 102.866 721.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire343}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(721.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire343) [list 102.866 721.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire337}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(721.17*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire337) [list 102.866 721.17 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire331}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(720.9*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire331) [list 102.866 720.9 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire325}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(720.63*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire325) [list 102.866 720.63 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire393}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire393) [list 102.878 624.24 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire387}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire387) [list 102.878 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire381}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(624.78*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire381) [list 102.878 624.78 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire375}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(625.05*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire375) [list 102.878 625.05 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire369}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(625.32*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire369) [list 102.878 625.32 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire363}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(625.59*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire363) [list 102.878 625.59 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire351}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(625.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire351) [list 102.878 625.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire345}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(626.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire345) [list 102.878 626.13 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire339}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(626.4*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire339) [list 102.878 626.4 0.6479999999999961 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire333}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(626.67*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire333) [list 102.878 626.67 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire327}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(102.87*$ot_gap_dbu)}] [expr {round(626.94*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire327) [list 102.878 626.94 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10327}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(145.908*$ot_gap_dbu)}] [expr {round(1315.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10327) [list 145.906 1315.44 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10374}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(145.908*$ot_gap_dbu)}] [expr {round(1315.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10374) [list 145.906 1315.71 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10356}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(178.09199999999998*$ot_gap_dbu)}] [expr {round(304.56*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10356) [list 178.102 304.56 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire10403}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(178.09199999999998*$ot_gap_dbu)}] [expr {round(304.83*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10403) [list 178.102 304.83 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire10394}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(178.146*$ot_gap_dbu)}] [expr {round(995.76*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10394) [list 178.134 995.76 0.6480000000000246 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10347}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(178.146*$ot_gap_dbu)}] [expr {round(996.03*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10347) [list 178.134 996.03 0.6480000000000246 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10339}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(180.09*$ot_gap_dbu)}] [expr {round(32.13*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10339) [list 180.089 32.13 0.6479999999999961 0.27000000000001023]
set ot_gap_i [$ot_gap_blk findInst {wire10386}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(180.09*$ot_gap_dbu)}] [expr {round(31.86*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10386) [list 180.089 31.86 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10317}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(203.57999999999998*$ot_gap_dbu)}] [expr {round(624.24*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10317) [list 203.567 624.24 0.6479999999999961 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire10364}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(203.57999999999998*$ot_gap_dbu)}] [expr {round(624.51*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10364) [list 203.567 624.51 0.6479999999999961 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10328}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(277.236*$ot_gap_dbu)}] [expr {round(1315.44*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10328) [list 277.233 1315.44 0.6479999999999677 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10375}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(277.236*$ot_gap_dbu)}] [expr {round(1315.71*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10375) [list 277.233 1315.71 0.6479999999999677 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10341}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(311.84999999999997*$ot_gap_dbu)}] [expr {round(351.81*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10341) [list 311.855 351.81 0.6479999999999677 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10388}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(311.84999999999997*$ot_gap_dbu)}] [expr {round(351.54*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10388) [list 311.855 351.54 0.6479999999999677 0.27000000000003865]
set ot_gap_i [$ot_gap_blk findInst {wire10366}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(323.514*$ot_gap_dbu)}] [expr {round(723.33*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10366) [list 323.501 723.33 0.6480000000000246 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10319}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(323.568*$ot_gap_dbu)}] [expr {round(723.06*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10319) [list 323.587 723.06 0.6480000000000246 0.2700000000000955]
set ot_gap_i [$ot_gap_blk findInst {wire10342}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient MX
$ot_gap_i setLocation [expr {round(419.418*$ot_gap_dbu)}] [expr {round(351.81*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10342) [list 419.406 351.81 0.6479999999999677 0.2699999999999818]
set ot_gap_i [$ot_gap_blk findInst {wire10389}]
if {$ot_gap_i eq "NULL"} { error "allocated gap instance missing" }
$ot_gap_i setOrient R0
$ot_gap_i setLocation [expr {round(419.418*$ot_gap_dbu)}] [expr {round(351.54*$ot_gap_dbu)}]
$ot_gap_i setPlacementStatus FIRM
set ot_gap_moved(wire10389) [list 419.406 351.54 0.6479999999999677 0.2699999999999818]
