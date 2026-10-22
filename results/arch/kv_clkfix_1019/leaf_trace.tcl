read_db /base/6_final.odb
set blk [ord::get_db_block]
proc rep {n} {
  set i [$::blk findInst [string map {"\[" "\\\[" "\]" "\\\]"} $n]]
  if {$i eq "NULL"} { puts "NOINST $n"; return }
  foreach it [$i getITerms] {
    if {[[$it getMTerm] getSigType] ne "CLOCK" && [[$it getMTerm] getName] ne "CLK"} continue
    set net [$it getNet]
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set d [$t getInst]; set drv "[$d getName] [[$d getMaster] getName] [$d getLocation]" } }
    set xs {}; set ys {}
    foreach t [$net getITerms] { lassign [[$t getInst] getLocation] x y; lappend xs $x; lappend ys $y }
    set wl -
    puts "LEAF $n at [$i getLocation] net [$net getName] sinks [llength [$net getITerms]] drv {$drv} bbox x [tcl::mathfunc::min {*}$xs]..[tcl::mathfunc::max {*}$xs] y [tcl::mathfunc::min {*}$ys]..[tcl::mathfunc::max {*}$ys] wire $wl"
    # walk up one level
    set dinst [lindex $drv 0]
    if {$dinst ne ""} {
      set di [$::blk findInst $dinst]
      foreach t2 [$di getITerms] { if {[$t2 isInputSignal]} { set n2 [$t2 getNet]; if {$n2 eq "NULL"} continue; set l2 -; foreach t3 [$n2 getITerms] { if {[$t3 isOutputSignal]} { set d3 [$t3 getInst]; puts "  UP [$n2 getName] sinks [llength [$n2 getITerms]] drv [$d3 getName] [[$d3 getMaster] getName] [$d3 getLocation] wire $l2" } } } }
    }
  }
}
proc up2 {inst} { foreach t2 [$inst getITerms] { if {[$t2 isInputSignal]} { set n2 [$t2 getNet]; if {$n2 eq "NULL"} continue; foreach t3 [$n2 getITerms] { if {[$t3 isOutputSignal]} { set d3 [$t3 getInst]; puts "    UP2 [$n2 getName] sinks [llength [$n2 getITerms]] drv [$d3 getName] [$d3 getLocation]"; return $d3 } } } }; return "" }
foreach n {{i_hroot_ES__ot_q[164]$_DFF_P_} {i_hroot_ES__ot_q[88]$_DFF_P_} {i_hroot_ES__ot_q[264]$_DFF_P_} {rst_n__ot_q$_DFF_P_} {i_hroot_WS__ot_q[18]$_DFF_P_} {i_hroot_EN__ot_q[100]$_DFF_P_}} { rep $n }
