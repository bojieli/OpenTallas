foreach l $::env(PLIBS) { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [get_clocks clk]
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set blk [ord::get_db_block]
set f [open $::env(OUT) w]
puts $f "#inst master x y in_arr out_arr in_slew fanout drv_inst in_net"
# BFS from clk port
set bt [$blk findBTerm clk]
set q [list [$bt getNet]]
set seen {}
while {[llength $q]} {
  set net [lindex $q 0]; set q [lrange $q 1 end]
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set i [$it getInst]; set m [$i getMaster]
    if {[$m isSequential] || [$m getType] eq "BLOCK"} continue
    set nm [$i getName]
    if {[dict exists $seen $nm]} continue
    dict set seen $nm 1
    set o ""; foreach t [$i getITerms] { if {[$t isOutputSignal]} { set o $t } }
    if {$o eq "" || [$o getNet] eq "NULL"} continue
    set on [$o getNet]
    set ip [get_pins "$nm/[[$it getMTerm] getName]"]; set op [get_pins "$nm/[[$o getMTerm] getName]"]
    set fo 0; foreach t [$on getITerms] { if {[$t isInputSignal]} { incr fo } }
    set drv "PORT"; foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv [[$t getInst] getName] } }
    set l [$i getLocation]
    puts $f "$nm [$m getName] [expr {[lindex $l 0]/double($dbu)}] [expr {[lindex $l 1]/double($dbu)}] [get_property $ip arrival_max_rise] [get_property $op arrival_max_rise] [get_property $ip slew_max_rise] $fo $drv [$net getName]"
    lappend q $on
  }
}
close $f
puts TREE_DONE
