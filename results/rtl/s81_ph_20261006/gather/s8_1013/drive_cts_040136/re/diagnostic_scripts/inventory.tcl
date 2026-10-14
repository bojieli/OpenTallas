read_db [lindex [glob /work/results/asap7/*/base/4_1_cts.odb] 0]
set b [ord::get_db_block]
set counts [dict create]
foreach i [$b getInsts] {
 set m [[$i getMaster] getName]
 set n [$i getName]
 dict incr counts $m
 if {[regexp {^(ot_inhold_|ot_outhold_|ot_ihdrv_|ot_ohdrv_|hold|holdfix|hold_buffer)} $n]} {puts "S81_STAGE_CELL $n $m"}
}
dict for {m n} $counts {puts "S81_MASTER_COUNT $m $n"}
exit
