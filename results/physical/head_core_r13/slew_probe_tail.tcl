set block [ord::get_db_block]
set dbu [$block getDefUnits]
foreach pn $::probe_pins {
  set p [get_pins $pn]
  set net [get_nets -of_objects $p]
  set nn [get_full_name $net]
  set dn [$block findNet $nn]
  set wl -1
  set w [$dn getWire]
  if {$w ne "NULL"} { set wl [expr {[$w getLength]/double($dbu)}] }
  set xs {}; set ys {}; set desc {}
  foreach it [$dn getITerms] {
    set inst [$it getInst]
    set bb [$inst getBBox]
    lappend xs [expr {[$bb xMin]/double($dbu)}]; lappend ys [expr {[$bb yMin]/double($dbu)}]
    lappend desc "[$inst getName]/[[$it getMTerm] getName]([[$inst getMaster] getName])@[format %.1f [expr {[$bb xMin]/double($dbu)}]],[format %.1f [expr {[$bb yMin]/double($dbu)}]][expr {[$it isOutputSignal]?"*DRV":""}]"
  }
  set bw [expr {[tcl::mathfunc::max {*}$xs]-[tcl::mathfunc::min {*}$xs]}]
  set bh [expr {[tcl::mathfunc::max {*}$ys]-[tcl::mathfunc::min {*}$ys]}]
  puts "PROBE pin $pn net $nn wire_um [format %.1f $wl] bbox [format %.1f $bw]x[format %.1f $bh] terms [llength $desc] :: [join $desc { }]"
}
