# HBM-R16/ISL: plan-model GEO (core_islands/core_infra_htree format) from a placed core ODB: every sequential
# clock pin (FF/latch/ICG CLK) + every macro with its clock pin, whatever net drives it (pre-CTS buffers included).
# env ODB OUT ENTRY "x y"
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [format %.3f [expr {$v / double($::u)}]] }
set f [open $::env(OUT) w]
set d [$b getDieArea]; puts $f "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
puts $f "CORE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
lassign $::env(ENTRY) ex ey; puts $f "PIN ck $ex $ey"
set ns 0; set nm 0
foreach i [$b getInsts] {
  set m [$i getMaster]
  if {[$m isBlock]} {
    set r [$i getBBox]; set ck ""
    foreach it [$i getITerms] { set mt [$it getMTerm]; set n [string tolower [$mt getName]]
      if {[$mt getSigType] eq "CLOCK" || [string match *clk* $n] || [string match *clock* $n]} {
        set ib [$it getBBox]; if {$ib eq ""} continue
        set ck "CK [um [expr {([$ib xMin]+[$ib xMax])/2}]] [um [expr {([$ib yMin]+[$ib yMax])/2}]]"; break } }
    puts $f "MACRO [$i getName] [$m getName] [um [$r xMin]] [um [$r yMin]] [um [$r xMax]] [um [$r yMax]] $ck"; incr nm; continue
  }
  set mn [$m getName]
  if {![regexp {^(DFF|SDF|DHL|DLL|ICG|ASYNC)} $mn]} continue
  foreach it [$i getITerms] { set mt [$it getMTerm]
    if {[$mt getSigType] eq "CLOCK" || [$mt getName] in {CLK CK GCLK}} {
      set ib [$it getBBox]; set net [$it getNet]; set nn [expr {$net eq "NULL" ? "-" : [$net getName]}]
      puts $f "SINK [um [expr {([$ib xMin]+[$ib xMax])/2}]] [um [expr {([$ib yMin]+[$ib yMax])/2}]] $mn [$i getName] [$mt getName] $nn"; incr ns; break } }
}
close $f
puts "DUMP_SEQ_GEO sinks $ns macros $nm"
exit
