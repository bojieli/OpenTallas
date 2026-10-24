# CP1-R10 review dump: every register's (x, y, CK rise arrival) and the clock tap pins, from a CTS ODB (TT, placement RC)
set PL /OpenROAD-flow-scripts/flow/platforms/asap7
read_db $::env(ODB)
foreach f [glob $PL/lib/NLDM/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_sdc $::env(SDC)
source $PL/setRC.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]
set fh [open $::env(OUT) w]
foreach bt [$blk getBTerms] {
  set n [$bt getName]
  if {[regexp {^clk(_t[0-9]+)?$} $n]} { set bb [$bt getBBox]; puts $fh "TAP $n [expr {[$bb xCenter]/double($dbu)}] [expr {[$bb yCenter]/double($dbu)}]" }
}
set per [get_property [get_clocks clk] period]
foreach c [all_registers -cells] {
  set nm [get_full_name $c]
  set ck ""
  foreach p [get_pins -of_objects $c] { if {[get_property $p lib_pin_name] eq "CLK"} { set ck $p } }
  if {$ck eq ""} continue
  if {[catch {set a [get_property $ck arrival_max_rise]}] || $a eq ""} continue
  if {$a >= $per/2} { set a [expr {$a - $per/2}] }
  set i [sta::sta_to_db_inst $c]
  if {$i eq "NULL"} { set i [$blk findInst [string map {\\ {}} $nm]] }
  if {$i eq "NULL"} continue
  set bb [$i getBBox]
  puts $fh "FF [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}] [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}] [format %.1f $a] [$i getPlacementStatus] $nm"
}
close $fh
set fh [open $::env(OUT).cells w]
foreach i [$blk getInsts] { set bb [$i getBBox]; puts $fh "[expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}] [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}] [expr {[$bb getDX]*[$bb getDY]/double($dbu)/$dbu}] [[$i getMaster] getName]" }
close $fh
