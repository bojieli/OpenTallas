source /work/hooks/pre_cts_ot_cts_fix.tcl
rename repair_timing ::ot_ctrl_repair_original
proc repair_timing {args} {
  set b [ord::get_db_block]
  set hn [$b findNet ot_inhold_n00001]
  set hd [$b findInst ot_ihdrv_00001]
  puts "CTRL_REPAIR_TRACE protected net=[$hn isDoNotTouch] driver=[$hd isDoNotTouch] args=$args"
  if {[lsearch -exact $args -setup]>=0 && [lsearch -exact $args -hold]<0} {
    lappend args -sequence {sizeup} -max_iterations 1 -skip_last_gasp
    puts "CTRL_REPAIR_DIAGNOSTIC isolate one setup SizeUpMove iteration; diagnostic only, hold and STA checks unchanged"
  }
  return [::ot_ctrl_repair_original {*}$args]
}
