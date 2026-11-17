# CAPSKEW-ECO: plain detailed_route on the guided DB (the kit's ORFS arguments), list unrouted nets, write the DB.
# Environment: X_IN, X_OUT, X_DIR, X_THREADS (default 8).  Only the ripped (wire-less) nets are routed; every kept wire stays.
set in $::env(X_IN); set out $::env(X_OUT); set dir $::env(X_DIR)
set_thread_count [expr {[info exists ::env(X_THREADS)] ? $::env(X_THREADS) : 8}]
read_db $in
detailed_route -output_drc $dir/5_route_drc.rpt -output_maze $dir/maze.log -droute_end_iter 64 -verbose 1 -drc_report_iter_step 5
set blk [ord::get_db_block]; set n 0; set fp [open $dir/unrouted.txt w]
foreach net [$blk getNets] {
  if {[$net getSigType] ni {SIGNAL CLOCK}} continue
  if {[$net getITermCount] + [$net getBTermCount] < 2} continue
  if {[$net isSpecial]} continue
  if {[$net getWire] eq "NULL"} { puts $fp [$net getName]; incr n }
}
close $fp
puts "CAPSKEW_UNROUTED $n"
puts "CAPSKEW_OBSTRUCTIONS [llength [$blk getObstructions]]"
write_db $out
puts "CAPSKEW_ROUTE_DONE"
