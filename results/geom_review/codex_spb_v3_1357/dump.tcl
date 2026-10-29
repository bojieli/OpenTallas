read_db /src/probe_grt.odb
set b [ord::get_db_block]
set u [expr {double([$b getDbUnitsPerMicron])}]
set f [open /out/actual.tsv w]
foreach i [$b getInsts] {
 set m [$i getMaster];set bb [$i getBBox]
 puts $f "I\t[$i getName]\t[$m getName]\t[$i getOrient]\t[expr {[$bb xMin]/$u}]\t[expr {[$bb yMin]/$u}]\t[expr {[$bb xMax]/$u}]\t[expr {[$bb yMax]/$u}]"
 if {[$m isBlock]} {foreach mt [$m getMTerms] {if {[$mt getSigType] in {POWER GROUND}} continue
 foreach mp [$mt getMPins] {foreach p [$mp getGeometry] {
  set l [$p getTechLayer];if {$l eq "NULL"} continue
  puts $f "P\t[$i getName]\t[$mt getName]\t[$l getName]\t[expr {([$p xMin]+[$p xMax])/(2*$u)}]\t[expr {([$p yMin]+[$p yMax])/(2*$u)}]"
 }}}}
}
close $f
