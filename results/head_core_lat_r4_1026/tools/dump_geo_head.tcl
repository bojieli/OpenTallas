# HEAD-CORE-LAT-R4: plan-model geometry from a placed core ODB (format = QC SU geo: DIE/CORE/PIN ck/MACRO/SINK)
# SINK = every sequential std-cell clock pin (CLK) and every macro clock pin, whatever net it is on (pre-CTS).
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
proc um {v} { return [format %.3f [expr {$v / double($::u)}]] }
set d [$b getDieArea]; puts $f "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
set c [$b getCoreArea]; puts $f "CORE [um [$c xMin]] [um [$c yMin]] [um [$c xMax]] [um [$c yMax]]"
foreach bt [$b getBTerms] { set nm [$bt getName]
  if {[regexp {^(clk|ck|ft_ck0_i|ft_mesh_i)$} $nm]} { set bb [$bt getBBox]
    puts $f "PORT $nm [um [expr {([$bb xMin]+[$bb xMax])/2}]] [um [expr {([$bb yMin]+[$bb yMax])/2}]]" } }
set ns 0; set nm 0; array set nets {}
foreach i [$b getInsts] {
  set m [$i getMaster]
  foreach it [$i getITerms] {
    set mt [$it getMTerm]; set pn [$mt getName]
    if {[$m isBlock]} {
      if {![regexp -nocase {^(clk|ck|clock)$} $pn]} continue
      set r [$i getBBox]; set ib [$it getBBox]
      set n [$it getNet]; set nn [expr {$n eq "NULL" ? "-" : [$n getName]}]
      puts $f "MACRO [$i getName] [$m getName] [um [$r xMin]] [um [$r yMin]] [um [$r xMax]] [um [$r yMax]] $pn [um [expr {([$ib xMin]+[$ib xMax])/2}]] [um [expr {([$ib yMin]+[$ib yMax])/2}]] $nn"; incr nm; continue
    }
    if {[$mt getSigType] ne "CLOCK" && $pn ne "CLK"} continue
    if {![string match "*DFF*" [$m getName]] && ![string match "*SDF*" [$m getName]] && ![string match "*ICG*" [$m getName]]} continue
    set ib [$it getBBox]; set n [$it getNet]; set nn [expr {$n eq "NULL" ? "-" : [$n getName]}]
    incr nets($nn)
    puts $f "SINK [um [expr {([$ib xMin]+[$ib xMax])/2}]] [um [expr {([$ib yMin]+[$ib yMax])/2}]] [$m getName] [$i getName] $pn $nn"; incr ns
  }
}
foreach k [array names nets] { puts $f "NET $k $nets($k)" }
close $f
puts "DUMP_GEO sinks $ns macros $nm nets [array size nets]"
exit
