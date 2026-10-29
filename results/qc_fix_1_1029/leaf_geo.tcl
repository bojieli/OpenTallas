# QC-FIX-1: planned clock leaf -> sink distances on a placed ODB (every net driven by an mp_ck_* cell that has FF sinks)
read_db $::env(ODB)
set b [ord::get_db_block]
set fh [open $::env(OUT) w]
foreach i [$b getInsts] {
  set n [$i getName]
  if {![string match "mp_ck_*" $n]} continue
  set y [$i findITerm Y]; if {$y eq "NULL"} continue
  set net [$y getNet]; if {$net eq "NULL"} continue
  set dxy [$y getAvgXY]
  foreach it [$net getITerms] {
    if {[$it isOutputSignal]} continue
    if {[[$it getMTerm] getName] ni {CLK clk}} continue
    set s [$it getAvgXY]
    puts $fh "L $n [expr {[lindex $dxy 1]/1000.0}] [expr {[lindex $dxy 2]/1000.0}] [[$it getInst] getName] [expr {[lindex $s 1]/1000.0}] [expr {[lindex $s 2]/1000.0}]"
  }
}
close $fh
