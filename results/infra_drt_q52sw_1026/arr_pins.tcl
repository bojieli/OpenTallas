source /d/sta_head.tcl
set blk [ord::get_db_block]
report_wns
set fo [open $::env(OT_OUT) w]
foreach n [$blk getNets] {
  set drv {}; foreach it [$n getITerms] { if {[$it isOutputSignal]} { lappend drv $it } }
  if {[llength $drv] < 2} continue
  puts "MESH_NET [$n getName] drivers [llength $drv]"
  foreach it $drv { set i [$it getInst]; set p "[$i getName]/A"
    set pin [get_pins $p]
    puts $fo "$p [get_property $pin arrival_max_rise] [get_property $pin arrival_min_rise] [get_property $pin slew_max_rise]" }
}
close $fo
