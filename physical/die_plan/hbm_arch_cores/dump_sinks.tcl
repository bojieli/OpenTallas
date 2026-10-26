read_db $::env(ODB)
set blk [ord::get_db_block]
set dbu [$blk getDefUnits]
set f [open $::env(OUT) w]
set die [$blk getDieArea]
puts $f "DIE [expr [$die xMin]/double($dbu)] [expr [$die yMin]/double($dbu)] [expr [$die xMax]/double($dbu)] [expr [$die yMax]/double($dbu)]"
foreach bt [$blk getBTerms] {
  if {[$bt getSigType] == "CLOCK" || [string match -nocase "*clk*" [$bt getName]]} {
    set bb [$bt getBBox]
    puts $f "CLKPIN [$bt getName] [expr ([$bb xMin]+[$bb xMax])/2.0/$dbu] [expr ([$bb yMin]+[$bb yMax])/2.0/$dbu]"
  }
}
foreach inst [$blk getInsts] {
  set m [$inst getMaster]
  set bb [$inst getBBox]
  set isblk [expr {[$m getType] == "BLOCK"}]
  if {$isblk} {
    puts $f "MACRO [$inst getName] [$m getName] [expr [$bb xMin]/double($dbu)] [expr [$bb yMin]/double($dbu)] [expr [$bb xMax]/double($dbu)] [expr [$bb yMax]/double($dbu)]"
  }
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    set nm [$mt getName]
    if {[$mt getSigType] == "CLOCK" || $nm == "CLK" || ($isblk && [string match -nocase "*clk*" $nm])} {
      set n [$it getNet]
      if {$n == "NULL"} continue
      set b [$it getBBox]
      puts $f "SINK [$m getName] [expr ([$b xMin]+[$b xMax])/2.0/$dbu] [expr ([$b yMin]+[$b yMax])/2.0/$dbu] [$n getName]"
      break
    }
  }
}
close $f
