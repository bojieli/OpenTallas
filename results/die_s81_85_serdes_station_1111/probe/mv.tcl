# STATION: the three pad relays on the long hops move to the hop midpoint (reset_taps placement overlay, sites only)
set dbu [$blk getDbUnitsPerMicron]
foreach {n x y} {u_rrl_59 1803.60 228.96 u_rrl_79 1447.20 228.96 u_rrl_88 1086.48 228.96} {
  foreach i [$blk getInsts] {
    if {[string match "u_bound.$n/*" [$i getName]]} {
      lassign [$i getLocation] ox oy
      $i setLocation [expr {int($x*$dbu)}] [expr {int($y*$dbu)}]
      puts "REL moved [$i getName] from [expr {$ox/double($dbu)}] to $x"
    }
  }
}
