# r7a (HBM-SMATT9): the r6c post_grt_audit asserted native PG on 5_1_grt BEFORE the final global_connect
# (native_pg_binding.tcl: ot_pg_collect_all_native is documented "Run after final global_connect").
# Standard mode (OT_PG_STRICT unset): the final stage's global_connect binds every non-dont_touch cell.
# This audit classifies the pre-connect gaps, runs exactly that global_connect in memory (odb NOT written) and asserts.
read_db $::env(R7_ODB)
source /src/physical/common_flow/native_pg_binding.tcl
set b [ord::get_db_block]
set rep [ot_pg_collect_all_native $b [ot_pg_prepare $b]]
set cls [dict create]; set dt 0
foreach f [dict get $rep failures] {
  set n [dict get $f instance]; regsub {[0-9_]+$} $n {} p
  dict incr cls "[dict get $f master]:$p"
  set i [$b findInst $n]; if {$i ne "NULL" && [$i isDoNotTouch]} {incr dt}
}
puts "R7_PG_PRE failures=[dict get $rep failure_count] checked=[dict get $rep checked] dont_touch_unbound=$dt"
foreach {k v} [lrange [lsort -stride 2 -index 1 -integer -decreasing $cls] 0 39] {puts "R7_PG_PRE_CLASS $k $v"}
puts "R7_PG_RULES [llength [$b getGlobalConnects]]"
global_connect
ot_pg_assert_all_native $b [ot_pg_prepare $b]
puts R7_PG_POST_CONNECT_ALL_BOUND
