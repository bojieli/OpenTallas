source /work/hooks/pre_cts_ot_cts_fix.tcl
rename repair_timing ::ot_ctrl_repair_original
proc repair_timing {args} {
  set b [ord::get_db_block]
  set hn [$b findNet ot_inhold_n00001]
  set hd [$b findInst ot_ihdrv_00001]
  puts "CTRL_REPAIR_TRACE protected net=[$hn isDoNotTouch] driver=[$hd isDoNotTouch] args=$args"
  if {[lsearch -exact $args -setup]>=0 && [lsearch -exact $args -hold]<0} {
    lappend args -sequence {clone} -max_iterations 1 -skip_last_gasp
    puts "CTRL_REPAIR_DIAGNOSTIC isolate one setup CloneMove iteration; diagnostic only, hold and STA checks unchanged"
  }
  set code [catch {::ot_ctrl_repair_original {*}$args} result opts]
  if {$code} {
    puts "CTRL_CLONE_FAILURE $result"
    foreach inst [$b getInsts] {
      if {![string match clone* [$inst getName]]} {continue}
      puts "CTRL_CLONE_INSTANCE [$inst getName] master=[[$inst getMaster] getName] donttouch=[$inst isDoNotTouch]"
      foreach term [$inst getITerms] {
        set net [$term getNet]
        if {$net eq "NULL"} {puts "CTRL_CLONE_TERM [[$term getMTerm] getName] UNCONNECTED"} else {puts "CTRL_CLONE_TERM [[$term getMTerm] getName] [$net getName] donttouch=[$net isDoNotTouch]"}
      }
    }
    write_db /work/clone_failure.odb
    return -options $opts $result
  }
  error "CTRL_CLONE_DIAGNOSTIC_STOP_AFTER_REPAIR_CALL"
}
