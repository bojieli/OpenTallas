# CORES-EARLY-5 probe: dump every clock sink (gated or direct) with its gating ICG and placed xy (um).
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
proc um {v} { return [expr {$v / double($::u)}] }
proc ctr {i} { set bb [$i getBBox]; return [list [um [expr {([$bb xMin]+[$bb xMax])/2}]] [um [expr {([$bb yMin]+[$bb yMax])/2}]]] }
set f [open $::env(OUT) w]
set clk [$b findNet $::env(CLKNET)]
proc walk {net dom f} {
  set q [list $net]
  while {[llength $q]} {
    set n [lindex $q 0]; set q [lrange $q 1 end]
    foreach it [$n getITerms] {
      if {[$it isOutputSignal]} continue
      set j [$it getInst]; set jm [$j getMaster]; set jn [$jm getName]
      if {[string match {ICG*} $jn] && $dom eq "ROOT"} {
        set xy [ctr $j]; puts $f "GATE [$j getName] [lindex $xy 0] [lindex $xy 1]"
        foreach ot [$j getITerms] { if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} { walk [$ot getNet] [$j getName] $f } }
        continue
      }
      if {[string match {*BUF*} $jn] || [string match {*INV*} $jn]} {
        foreach ot [$j getITerms] { if {[$ot isOutputSignal] && [$ot getNet] ne "NULL"} { lappend q [$ot getNet] } }; continue }
      set xy [ctr $j]
      puts $f [format "SINK %s %s %.3f %.3f %d %s" $dom [$j getName] [lindex $xy 0] [lindex $xy 1] [$jm isBlock] [[$it getMTerm] getName]]
    }
  }
}
walk $clk ROOT $f
set bb [$b getDieArea]; puts $f "DIE [um [$bb xMax]] [um [$bb yMax]]"
close $f
exit
