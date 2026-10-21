# Physical ownership of the exact placed-sink copy recut; no timing exception.
set q13_block [ord::get_db_block]
set q13_dbu [$q13_block getDbUnitsPerMicron]
set q13_owners [dict create u_qkorr_0 E0 u_26155 W0 u_68244 W0 u_68245 W0 u_68246 W0 u_68247 W0 u_68248 W0 u_68249 W0 u_68250 W0 u_34391 W0 u_68441 W0 u_68442 W1 u_34415 W0 u_68430 W1 u_34461 W0 u_68389 W0 u_68390 W0 u_68391 W0 u_68392 W0 u_68393 W0 u_68394 W1 u_68395 W1 u_39317 W0 u_68656 W1 u_68723 W1 u_39464 W0 u_68027 W0 u_68028 W0 u_68029 W0 u_68030 W0 u_68031 W1 u_39465 W0 u_68022 W0 u_68023 W0 u_68024 W0 u_68025 W0 u_68026 W0 u_68665 W0 u_68724 W0 u_68738 W1 u_39533 E0 u_68231 W0 u_68232 W0 u_68233 W0 u_68234 W1 u_68235 W1 u_qkorr_13_0 W1 u_39534 W0 u_68276 W0 u_68277 W0 u_68278 W0 u_68279 W0 u_68280 W0 u_68281 W1 u_68282 W1 u_68283 W1 u_68695 W1 u_39570 W0 u_68226 W1 u_68227 W1 u_68228 W1 u_68229 W1 u_68230 W1 u_39607 W0 u_68221 W1 u_68222 W1 u_68223 W1 u_68224 W1 u_68225 W1 u_39654 W0 u_67666 W0 u_qkorr_13_1 W1 u_39716 E0 u_67845 E0 u_67846 E1 u_67847 E1 u_68662 E1 u_68032 W0 u_68033 W0 u_68034 W0 u_68035 W0 u_68036 W1]
set q13_zones [dict create W0 {2.16 129.6 453.6 410.4} W1 {2.16 410.4 453.6 691.2} E0 {453.6 367.2 775.44 475.2} E1 {453.6 475.2 615.6 691.2}]
set q13_groups {}; set q13_counts {}
dict for {z bx} $q13_zones {
 set region [odb::dbRegion_create $q13_block ot_q13_$z]
 $region setRegionType INCLUSIVE
 lassign $bx x0 y0 x1 y1
 odb::dbBox_create $region [expr {round($x0*$q13_dbu)}] [expr {round($y0*$q13_dbu)}] [expr {round($x1*$q13_dbu)}] [expr {round($y1*$q13_dbu)}]
 dict set q13_groups $z [odb::dbGroup_create $region ot_q13_$z]
 dict set q13_counts $z 0
}
set q13_seen {}
foreach i [$q13_block getInsts] {
 set root [regsub {[/.$].*$} [$i getName] {}]
 if {![dict exists $q13_owners $root]} continue
 if {[$i isFixed] || [[$i getMaster] isBlock]} {error "CTLM13 copy unexpectedly fixed/hard: $root"}
 set old [$i getGroup]
 if {$old ne "NULL" && $old ne ""} {$old removeInst $i}
 set z [dict get $q13_owners $root]
 [dict get $q13_groups $z] addInst $i
 dict incr q13_counts $z
 dict set q13_seen $root 1
}
dict for {n z} $q13_owners {if {![dict exists $q13_seen $n]} {error "CTLM13 actual mapped copy absent: $n"}}
puts "CTLM13_COPY_REGIONS PASS owners=[dict size $q13_seen] cells=$q13_counts"
