read_db $::env(ODB)
set blk [ord::get_db_block]
set f [open $::env(OUT) w]
foreach i [$blk getInsts] { set m [$i getMaster]; if {[$m isFiller] || [string match TAPCELL* [$m getName]]} continue
  lassign [$i getLocation] x y; set ins {}; set outs {}
  foreach it [$i getITerms] { set n [$it getNet]; if {$n eq "NULL"} continue; set t [$n getSigType]; if {$t in {POWER GROUND}} continue
    if {[$it isOutputSignal]} {lappend outs [$n getName]} elseif {[$it isInputSignal]} { if {[[$it getMTerm] getSigType] eq "CLOCK" || [[$it getMTerm] getName] in {CLK}} continue; lappend ins [$n getName]} }
  puts $f "[$i getName]\t[$m getName]\t[expr {$x/1000.0}]\t[expr {$y/1000.0}]\t[join $ins " "]\t[join $outs " "]" }
foreach b [$blk getBTerms] { set n [$b getNet]; if {$n eq "NULL"} continue; set p [$b getBPins]; if {[llength $p]==0} continue; set bx [[lindex [[lindex $p 0] getBoxes] 0] xMin]; set by [[lindex [[lindex $p 0] getBoxes] 0] yMin]
  if {[$b getIoType] eq "INPUT"} {puts $f "PORT:[$b getName]\tPORT\t[expr {$bx/1000.0}]\t[expr {$by/1000.0}]\t\t[$n getName]"} else {puts $f "PORT:[$b getName]\tPORT\t[expr {$bx/1000.0}]\t[expr {$by/1000.0}]\t[$n getName]\t"} }
close $f
exit
