# Dump the placed clock sinks of the core clock port (default clk) as JSON [[x, y], ...] (um, type frame, inst bbox
# centre).  Pre-CTS DB: every register still hangs on the port net.  env ODB, OUT, PORT (default clk).
read_db $::env(ODB)
set blk [ord::get_db_block]; set u [$blk getDbUnitsPerMicron]
set port [expr {[info exists ::env(PORT)] ? $::env(PORT) : "clk"}]
set net [[$blk findBTerm $port] getNet]
set fh [open $::env(OUT) w]; puts -nonewline $fh "\["; set first 1; set n 0
foreach it [$net getITerms] {
  set b [[$it getInst] getBBox]
  set x [expr {([$b xMin]+[$b xMax])/2.0/$u}]; set y [expr {([$b yMin]+[$b yMax])/2.0/$u}]
  if {!$first} {puts -nonewline $fh ","}; set first 0
  puts -nonewline $fh [format "\[%.2f,%.2f\]" $x $y]; incr n
}
puts $fh "\]"; close $fh; puts "TAP_SINKS_DUMP $port $n -> $::env(OUT)"
