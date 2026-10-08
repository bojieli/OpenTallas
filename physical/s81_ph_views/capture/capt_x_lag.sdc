# CLAUDE S81-PH dsfd_capt_x with ot_ratio_cdc_fifo LAG 1 (u_x of every root): an entry mem[i] is published by wp_pub one
# write (stream) cycle after it is written, and the writer rewrites slot i only after the reader has retired it, so
# the read shadow sh[i] is consumed only while mem[i] is stable: mem -> sh is a data path bounded by one stream period
# (minus margin) with no hold relation.  Pointer / state arcs stay single-flop crossings (setup window, hold).
set ot_mem [get_cells -quiet {g_r*u_x.mem*}]
set ot_sh  [get_cells -quiet {g_r*u_x.sh*}]
if {[llength $ot_mem] && [llength $ot_sh]} {
  set_max_delay -ignore_clock_latency 700 -from $ot_mem -to $ot_sh
  set_false_path -hold -from $ot_mem -to $ot_sh
  puts "OT_CAPT_X_LAG mem->sh [llength $ot_mem] / [llength $ot_sh] cells"
}
