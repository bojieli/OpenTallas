# DIE-QC-35 (A0) round 2: clock-sink census of the GEOM PASS-COND 3_place (read-only)
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set fh [open $::env(OUT) w]
puts $fh "die [expr {[[$b getDieArea] xMax]/double($u)}] [expr {[[$b getDieArea] yMax]/double($u)}]"
proc walk {n depth path fh u} {
  foreach it [$n getITerms] {
    if {![$it isInputSignal]} continue
    set i [$it getInst]; set m [[$i getMaster] getName]; set bb [$i getBBox]
    set x [expr {([$bb xMin]+[$bb xMax])/2.0/$u}]; set y [expr {([$bb yMin]+[$bb yMax])/2.0/$u}]
    set pin [[$it getMTerm] getName]
    puts $fh [format "S\t%s\t%d\t%s\t%s\t%s\t%.3f\t%.3f\t%s" $path $depth [$i getName] $pin $m $x $y [$i getPlacementStatus]]
    if {[string match "ICG*" $m] && $pin eq "CLK"} {
      set o [[$i findITerm GCLK] getNet]
      if {$o ne "NULL"} {walk $o [expr {$depth+1}] "$path>[$i getName]" $fh $u}
    } elseif {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m]} {
      set o [[$i getFirstOutput] getNet]
      if {$o ne "NULL"} {walk $o [expr {$depth+1}] "$path>[$i getName]" $fh $u}
    }
  }
}
foreach bt [$b getBTerms] {
  if {[$bt getName] eq $::env(CKP)} {
    set n [$bt getNet]
    foreach bp [$bt getBPins] { foreach box [$bp getBoxes] { puts $fh "port [$bt getName] [expr {[$box xMin]/double($u)}] [expr {[$box yMin]/double($u)}]" } }
    walk $n 0 root $fh $u
  }
}
close $fh
puts "CENSUS_DONE"
