source /w/common.tcl
read_db /w/tr_q4.odb
set blk [ord::get_db_block]
set nc 0; set bad {}
foreach p [get_pins -hier * -filter "is_clock==1"] { set n [get_full_name [get_nets -of_objects $p]]; set dn [$blk findNet $n]
  if {$dn ne "NULL" && [$dn getSigType] ne "CLOCK"} { lappend bad $n } }
foreach i [$blk getInsts] { if {[string match a0t_* [$i getName]] || [string match a0cl*_root [$i getName]]} { foreach it [$i getITerms] { set n [$it getNet]; if {$n ne "NULL" && [$n getSigType] ne "CLOCK" && [$n getSigType] ne "POWER" && [$n getSigType] ne "GROUND"} { lappend bad [$n getName] } } } }
set bad [lsort -unique $bad]
puts "NONCLOCK_SIGTYPE_CLOCKNETS [llength $bad] [lrange $bad 0 20]"
foreach n [$blk getNets] { if {[$n getSigType] eq "CLOCK"} { incr nc } }
puts "CLOCK_SIGTYPE_NETS $nc"
