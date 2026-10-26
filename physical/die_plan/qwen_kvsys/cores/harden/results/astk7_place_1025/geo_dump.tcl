# PATH-KV-ASTK7 post-place geometry dump (read-only): every core cell + face-flop output chains + start/schedule_age nets
read_db $::env(ODB)
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
proc c {i} {global u; set q [$i getBBox]; return [format "%.3f\t%.3f" [expr {([$q xMin]+[$q xMax])/(2.0*$u)}] [expr {([$q yMin]+[$q yMax])/(2.0*$u)}]]}
set f [open $::env(OUT)/cells.tsv w]
foreach i [$b getInsts] { if {![[$i getMaster] isCore]} continue; puts $f "[$i getName]\t[[$i getMaster] getName]\t[c $i]" }
close $f
# face chains: from every face flop (ot_face_flops.txt first column) follow the output through single-sink INV/BUF
set f [open $::env(OUT)/chains.tsv w]
set fh [open $::env(FACEF) r]; set ffs [split [read $fh] \n]; close $fh
foreach line $ffs {
  set nm [lindex [split $line \t] 0]; if {$nm eq ""} continue
  set i [$b findInst $nm]; if {$i eq "NULL" || $i eq ""} continue
  set cur $i; set hops 0; set rec {}; set out 0
  while {$hops < 8} {
    set on ""
    foreach it [$cur getITerms] { if {[[$it getMTerm] getIoType] eq "OUTPUT" && [$it getNet] ne "NULL"} {set on [$it getNet]} }
    if {$on eq ""} break
    if {[llength [$on getBTerms]] > 0} {set out 1; break}
    set sinks {}; foreach it [$on getITerms] { if {[$it getInst] ne $cur} {lappend sinks [$it getInst]} }
    if {[llength $sinks] != 1} break
    set s [lindex $sinks 0]
    if {![regexp {^(INV|BUF|HB)} [[$s getMaster] getName]]} break
    lappend rec "$nm\t[c $i]\t[$s getName]\t[c $s]"; set cur $s; incr hops
  }
  if {$out} { foreach r $rec { puts $f $r } }
}
close $f
set f [open $::env(OUT)/nets.tsv w]
foreach i [$b getInsts] {
  set nm [$i getName]
  if {![regexp {u_ctl[./](start|schedule_age\\?\[[0-9]+\\?\])\$} $nm all key]} continue
  foreach it [$i getITerms] {
    if {[[$it getMTerm] getIoType] ne "OUTPUT" || [$it getNet] eq "NULL"} continue
    foreach s2 [[$it getNet] getITerms] { puts $f "$key\t[[$s2 getInst] getName]\t[[$s2 getMTerm] getName]\t[c [$s2 getInst]]" }
  }
}
close $f
puts ASTK7_GEO_DUMP_DONE
