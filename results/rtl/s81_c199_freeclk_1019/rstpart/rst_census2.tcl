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
set nff 0; set nasr 0; set ncopy 0
foreach i [$b getInsts] { set m [[$i getMaster] getName]; if {[regexp {^DFF} $m]} {incr nff}; if {[regexp {^DFFASR} $m]} {incr nasr}; if {[regexp {u_r[a-z0-9]*$|g_rr} [$i getName]] && [regexp {^DFF} $m]} {incr ncopy} }
puts "CENSUS FF $nff ASYNC_FF $nasr"
set hist {}
set maxr 0; set maxany 0
foreach n [$b getNets] {
  set drv ""
  foreach t [$n getITerms] { if {[[$t getMTerm] getIoType] eq "OUTPUT"} { set drv [[$t getInst] getMaster] } }
  if {$drv eq ""} continue
  if {![regexp {^DFF} [$drv getName]]} continue
  set s [walk $n]
  set r 0
  foreach x $s { if {[regexp {\|(RESETN|SETN)$} $x]} {incr r} }
  if {$r > 0} { lappend hist $r; if {$r > $maxr} {set maxr $r}; if {$r > 32} {puts "RSTDRV_GT32 $r [$n getName]"} }
  if {[llength $s] > 32 && $r == 0} { puts "DATA_GT32 [llength $s] [$n getName]" }
}
puts "RESET_DRIVERS [llength $hist] MAX $maxr"
foreach k [lsort -integer -unique $hist] { set c 0; foreach h $hist { if {$h == $k} {incr c} }; puts "HIST $k $c" }
set clk [$b findNet clk]; if {$clk ne "NULL"} { puts "CLK_SINKS [llength [$clk getITerms]]" }
