read_db /odb/3_place.odb
set b [ord::get_db_block];set d [ord::get_db];set m [$d findMaster BUFx4_ASAP7_75t_R]
foreach order {location_first orientation_first} {
 set i [odb::dbInst_create $b $m probe_$order]
 if {$order eq "location_first"} {$i setLocation 50000 100710;$i setOrient MX} else {$i setOrient MX;$i setLocation 50000 100710}
 set r [$i getBBox];puts "CLOCK_ORIENTATION_PROBE $order bbox=[$r xMin],[$r yMin],[$r xMax],[$r yMax]"
}
exit
