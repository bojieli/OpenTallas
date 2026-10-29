read_db /odb/3_place.odb
set blk [ord::get_db_block]
set f [open /out/reach.tsv w]
set n 0; set over 0; set mx 0; set mxn ""
foreach net [$blk getNets] {
  set st [$net getSigType]
  if {$st eq "POWER" || $st eq "GROUND"} continue
  set drv {}; set snk {}
  foreach it [$net getITerms] {
    set ok [$it getAvgXY]; if {[lindex $ok 0] == 0} continue
    set xy [list [expr {[lindex $ok 1]/1000.0}] [expr {[lindex $ok 2]/1000.0}]]
    if {[$it isOutputSignal]} {lappend drv $xy} else {lappend snk $xy}
  }
  foreach bt [$net getBTerms] {
    set bb [$bt getBBox]
    set xy [list [expr {([$bb xMin]+[$bb xMax])/2000.0}] [expr {([$bb yMin]+[$bb yMax])/2000.0}]]
    if {[$bt getIoType] eq "INPUT"} {lappend drv $xy} else {lappend snk $xy}
  }
  if {[llength $drv] == 0 || [llength $snk] == 0} continue
  set d0 [lindex $drv 0]; set m 0
  foreach s $snk { set dd [expr {abs([lindex $s 0]-[lindex $d0 0]) + abs([lindex $s 1]-[lindex $d0 1])}]; if {$dd > $m} {set m $dd} }
  incr n
  if {$m > 405} { incr over; puts $f "[$net getName]\t$st\t[format %.2f $m]\t[llength $snk]" }
  if {$m > $mx} {set mx $m; set mxn [$net getName]}
}
close $f
puts "REACH nets $n over405 $over max [format %.2f $mx] $mxn"
