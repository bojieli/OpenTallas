read_db /work/results/asap7/opentallas_ot_v41_bf_col_asap7_ref_gate/base/1_synth.odb
set b [ord::get_db_block]
proc walk {n depth} {
  set out {}
  foreach t [$n getITerms] {
    if {[[$t getMTerm] getIoType] ne "INPUT"} continue
    set i [$t getInst]; set m [[$i getMaster] getName]
    if {[regexp {^(BUF|INV)} $m]} {
      foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { set out [concat $out [walk [$o getNet] [expr {$depth+1}]]] } }
    } else { lappend out "[$i getName]|[[$t getMTerm] getName]|$m" }
  }
  return $out
}
foreach n [$b getNets] {
  set nm [$n getName]
  if {![regexp {rst} $nm]} continue
  set s [walk $n 0]
  if {[llength $s] > 32} {
    puts "NET [llength $s] $nm"
    array unset g; array set g {}
    foreach x $s { set inst [lindex [split $x |] 0]; regsub {\.[^.]*$} $inst {} pre; regsub -all {\\} $pre {} pre; incr g($pre) }
    foreach k [lsort [array names g]] { puts "  GRP $g($k) $k" }
  }
}
