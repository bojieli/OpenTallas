read_db $::env(ODB)
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
set mpf [dict create]
set f [open $::env(MPF)]; foreach n [split [read $f] "\n"] { if {$n ne ""} { dict set mpf $n 1 } }; close $f
set o [open $::env(OUT) w]
foreach i [$b getInsts] {
  set m [$i getMaster]; if {[$m isBlock]} continue
  set mn [$m getName]; if {[string match TAPCELL* $mn] || [string match FILL* $mn]} continue
  set bb [$i getBBox]
  set k [expr {[dict exists $mpf [$i getName]] ? "mpf" : ([string match *DFF* $mn] ? "ff" : "o")}]
  puts $o "[$i getName]\t$mn\t$k\t[format %.3f [expr {([$bb xMin]+[$bb xMax])/2.0/$u}]]\t[format %.3f [expr {([$bb yMin]+[$bb yMax])/2.0/$u}]]\t[format %.3f [expr {([$bb xMax]-[$bb xMin])/double($u)}]]"
}
close $o
puts DUMP_CELLS_DONE
