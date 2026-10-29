read_db /odb/2_floorplan.odb
set b [ord::get_db_block]; set u 1000.0
foreach n {PHY_EDGE_ROW_3260_4_Right_25274 PHY_EDGE_ROW_3260_4_Left_21954 PHY_EDGE_ROW_3260_3_Right_25273 PHY_EDGE_ROW_3260_3_Left_21953 PHY_EDGE_ROW_3260_5_Left_21955 PHY_EDGE_ROW_3260_2_Right_25272} { set i [$b findInst $n]; if {$i ne "NULL"} { set bb [$i getBBox]; puts "$n [expr [$bb xMin]/$u] [expr [$bb xMax]/$u] [expr [$bb yMin]/$u]" } }
foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { set bb [$i getBBox]; puts "MACRO [$i getName] [expr [$bb xMin]/$u] [expr [$bb xMax]/$u] [expr [$bb yMin]/$u] [expr [$bb yMax]/$u]" } }
