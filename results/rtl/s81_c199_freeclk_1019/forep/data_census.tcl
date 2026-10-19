# Transparent (through BUF/INV) data fan-out census per flop driver; loads grouped by 4-level hierarchy prefix.
set f [glob /work/results/asap7/*/base/1_synth.odb]
read_db $f
set b [ord::get_db_block]
proc walk {n} {
  set out {}
  foreach t [$n getITerms] {
    if {[[$t getMTerm] getIoType] ne "INPUT"} continue
    set i [$t getInst]; set m [[$i getMaster] getName]
    if {[regexp {^(BUF|INV)} $m]} {
      foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { set out [concat $out [walk [$o getNet]]] } }
    } else { lappend out "[$i getName]|[[$t getMTerm] getName]" }
  }
  return $out
}
set thr 32
if {[info exists ::env(OT_THR)]} { set thr $::env(OT_THR) }
set nd 0; set maxd 0
foreach n [$b getNets] {
  set drv ""
  foreach t [$n getITerms] { if {[[$t getMTerm] getIoType] eq "OUTPUT"} { set drv $t } }
  if {$drv eq ""} continue
  set di [$drv getInst]
  if {![regexp {^DFF} [[$di getMaster] getName]]} continue
  set s [walk $n]
  set r 0
  foreach x $s { if {[regexp {\|(RESETN|SETN)$} $x]} {incr r} }
  if {$r > 0} continue
  set L [llength $s]
  if {$L > $maxd} {set maxd $L}
  if {$L > $thr} {
    incr nd
    array unset g
    foreach x $s { set p [lindex [split $x |] 0]; set parts [split $p .]; set k [join [lrange $parts 0 4] .]; if {[info exists g($k)]} {incr g($k)} else {set g($k) 1} }
    set gl {}
    foreach k [array names g] { lappend gl "$g($k):$k" }
    set gl [lsort -decreasing -dictionary $gl]
    puts "DATA_GT $L [$di getName] [[$drv getMTerm] getName] groups=[llength $gl] [lrange $gl 0 5]"
  }
}
puts "DATA_DRIVERS_GT $nd MAX $maxd THR $thr"
