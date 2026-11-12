# X-TIER-OTC probe: per clock-like input port (fclk_in_*, clk*), the port location, sink count, bbox and farthest sink (um)
read_db $::env(ODB)
set blk [ord::get_db_block]; set u [$blk getDbUnitsPerMicron]
foreach bt [$blk getBTerms] {
  set n [$bt getName]
  if {![regexp {^(fclk_in_|clk_t|clk$)} $n]} continue
  set net [$bt getNet]; if {$net eq "NULL"} continue
  set bb [$bt getBBox]; set px [expr {([$bb xMin]+[$bb xMax])/2.0/$u}]; set py [expr {([$bb yMin]+[$bb yMax])/2.0/$u}]
  set k 0; set far 0; set fx 0; set fy 0; set x0 1e9; set y0 1e9; set x1 -1e9; set y1 -1e9
  foreach it [$net getITerms] {
    set inst [$it getInst]; lassign [$inst getLocation] ix iy; set ix [expr {$ix/double($u)}]; set iy [expr {$iy/double($u)}]
    incr k; set d [expr {abs($ix-$px)+abs($iy-$py)}]
    if {$d > $far} { set far $d; set fx $ix; set fy $iy }
    if {$ix<$x0} {set x0 $ix}; if {$iy<$y0} {set y0 $iy}; if {$ix>$x1} {set x1 $ix}; if {$iy>$y1} {set y1 $iy}
  }
  puts [format "REACH %-22s port(%.0f,%.0f) sinks %5d far %.0f at (%.0f,%.0f) bbox %.0f,%.0f-%.0f,%.0f" $n $px $py $k $far $fx $fy $x0 $y0 $x1 $y1]
}
