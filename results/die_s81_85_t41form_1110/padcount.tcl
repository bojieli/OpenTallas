read_db $::env(ODB)
set blk [ord::get_db_block]
set f [open $::env(NEW)]; set names [split [string trim [read $f]] "\n"]; close $f
foreach n $names {
  set n [string map {"\\" ""} $n]
  set i [$blk findInst $n]
  if {$i eq "NULL"} { puts "PADCNT MISSING $n"; continue }
  # walk forward through single-fanout buffers to the sink
  set cur $i; set sink "?"; set depth 0
  while {$depth < 50} {
    incr depth
    set on ""
    foreach it [$cur getITerms] { if {[$it isOutputSignal]} { set on [$it getNet] } }
    if {$on eq "" || $on eq "NULL"} { set sink "nonet"; break }
    set bts [$on getBTerms]
    if {[llength $bts]} { set sink "PORT [[lindex $bts 0] getName]"; break }
    set loads {}
    foreach it [$on getITerms] { if {[$it isInputSignal]} { lappend loads $it } }
    if {[llength $loads] != 1} { set sink "MULTI [llength $loads] [$on getName]"; break }
    set li [[lindex $loads 0] getInst]
    if {[lsearch -exact $names [$li getName]] >= 0 || [string match "hold*" [lindex [split [$li getName] /] end]]} { set cur $li; continue }
    set sink "PIN [$li getName]/[[[lindex $loads 0] getMTerm] getName]"; break
  }
  puts "PADCNT [$i getName] [[$i getMaster] getName] -> $sink"
}
