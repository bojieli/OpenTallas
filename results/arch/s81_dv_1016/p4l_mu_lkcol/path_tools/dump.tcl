# MU-DIE-S81/PATH: dump die-net pin geometry + macro bodies from the p4l3_rv2 place.odb (pre-repeater state)
read_db /work/place.odb
set blk [ord::get_db_block]; set dbu [$blk getDbUnitsPerMicron]
set f [open /work/out/obst.tsv w]
foreach inst [$blk getInsts] {
  set m [$inst getMaster]
  set bb [$inst getBBox]
  puts $f "[$inst getName]\t[$m getName]\t[$m isBlock]\t[expr {[$bb xMin]/double($dbu)}]\t[expr {[$bb yMin]/double($dbu)}]\t[expr {[$bb xMax]/double($dbu)}]\t[expr {[$bb yMax]/double($dbu)}]"
}
close $f
set f [open /work/out/nets.tsv w]
set n 0
foreach net [$blk getNets] {
  set its [$net getITerms]; set bts [$net getBTerms]
  if {[llength $its] + [llength $bts] < 2} { continue }
  set drv ""; set snk {}
  foreach it $its {
    set mt [$it getMTerm]
    set io [$mt getIoType]
    set ok [$it getAvgXY]
    if {[lindex $ok 0]} { set x [expr {[lindex $ok 1]/double($dbu)}]; set y [expr {[lindex $ok 2]/double($dbu)}] } else {
      set bb [[$it getInst] getBBox]; set x [expr {([$bb xMin]+[$bb xMax])/2.0/$dbu}]; set y [expr {([$bb yMin]+[$bb yMax])/2.0/$dbu}] }
    set e "[[$it getInst] getName]/[$mt getName]@[format %.2f $x],[format %.2f $y]"
    if {$io eq "OUTPUT" && $drv eq ""} { set drv $e } else { lappend snk $e }
  }
  foreach bt $bts {
    set e "PORT/[$bt getName]@0,0"
    set bp [$bt getBPins]
    if {[llength $bp]} { set bb [[lindex $bp 0] getBBox]; set e "PORT/[$bt getName]@[format %.2f [expr {[$bb xMin]/double($dbu)}]],[format %.2f [expr {[$bb yMin]/double($dbu)}]]" }
    if {[$bt getIoType] eq "INPUT" && $drv eq ""} { set drv $e } else { lappend snk $e }
  }
  puts $f "[$net getName]\t[$net isSpecial]\t[$net getSigType]\t$drv\t[join $snk { }]"
  incr n
}
close $f
puts "OT_DUMP nets=$n"
