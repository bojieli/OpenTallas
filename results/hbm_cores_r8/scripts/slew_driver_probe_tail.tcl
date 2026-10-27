set_propagated_clock [all_clocks]
set dbu [[ord::get_db_block] getDbUnitsPerMicron]
set seen {}
proc xy {inst} { set l [$inst getLocation]; return [list [expr {[lindex $l 0]/$::dbu.}] [expr {[lindex $l 1]/$::dbu.}]] }
proc pinfo {pn} {
  global seen
  set p [get_pins $pn]
  set it [sta::sta_to_db_pin $p]
  set dn [$it getNet]
  set nname [$dn getName]
  if {[dict exists $seen $nname]} return
  dict set seen $nname 1
  set xs {}; set ys {}; set n 0; set drv "?"
  foreach t [$dn getITerms] {
    set i [$t getInst]; lassign [xy $i] x y
    if {[$t isOutputSignal]} { set drv "[$i getName]/[[$t getMTerm] getName] [[$i getMaster] getName] ([format %.1f $x],[format %.1f $y]) inst_dt=[$i isDoNotTouch] src=[$i getSourceType]"; set drvi $i } elseif {[$t isInputSignal]} { lappend xs $x; lappend ys $y; incr n }
  }
  set wl -1; set w [$dn getWire]; if {$w ne "NULL"} { set wl [expr {[$w getLength]/$::dbu.}] }
  puts "NET $nname dt=[$dn isDoNotTouch] sig=[$dn getSigType] fanout $n wire_um [format %.1f $wl] loads x [format %.1f [tcl::mathfunc::min {*}$xs]]-[format %.1f [tcl::mathfunc::max {*}$xs]] y [format %.1f [tcl::mathfunc::min {*}$ys]]-[format %.1f [tcl::mathfunc::max {*}$ys]]"
  puts "  DRV $drv"
  set sn [sta::db_net_to_sta $dn]
  catch { puts "  CAP total [sta::format_capacitance [$sn capacitance [sta::cmd_corner] max] 3] pin [sta::format_capacitance [$sn pin_capacitance [sta::cmd_corner] max] 3] wire [sta::format_capacitance [$sn wire_capacitance [sta::cmd_corner] max] 3]" }
  foreach t [$drvi getITerms] {
    if {![$t isInputSignal]} continue
    set inet [$t getNet]; if {$inet eq "NULL"} continue
    foreach u [$inet getITerms] { if {[$u isOutputSignal]} { set ii [$u getInst]; lassign [xy $ii] ix iy; puts "  IN [[$t getMTerm] getName] net [$inet getName] <- [$ii getName] [[$ii getMaster] getName] ([format %.1f $ix],[format %.1f $iy]) fanout [expr {[llength [$inet getITerms]]-1}]" } }
  }
}
foreach pn $::viol { pinfo $pn }
