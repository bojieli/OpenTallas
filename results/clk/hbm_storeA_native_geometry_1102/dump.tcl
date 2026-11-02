read_db $::env(INPUT_ODB)
set b [ord::get_db_block]
set f [open /out/graph.tsv w]
puts $f "kind\towner\tmaster\tmastertype\tpin\tio\tsignal\tnet\tplacement\tx\ty"
foreach bt [$b getBTerms] {
 set n [$bt getNet];set nn "";if {$n ne "NULL"} {set nn [$n getName]}
 puts $f "BTERM\t[$bt getName]\t\t\t[$bt getName]\t[$bt getIoType]\t[$bt getSigType]\t$nn\t\t\t"
}
foreach inst [$b getInsts] {
 set m [$inst getMaster];set name [$inst getName];set master [$m getName];set type [$m getType];set place [$inst getPlacementStatus];set xy [$inst getOrigin];set x [lindex $xy 0];set y [lindex $xy 1]
 foreach it [$inst getITerms] {
  set mt [$it getMTerm];set sig [$mt getSigType];if {$sig eq "POWER" || $sig eq "GROUND"} {continue}
  set n [$it getNet];set nn "";if {$n ne "NULL"} {set nn [$n getName]}
  puts $f "ITERM\t$name\t$master\t$type\t[$mt getName]\t[$mt getIoType]\t$sig\t$nn\t$place\t$x\t$y"
 }
}
close $f
puts "NATIVE_SOURCE_GRAPH_DUMP_DONE"
