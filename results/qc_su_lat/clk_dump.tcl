# QC-SU-LAT: dump clock-tree cells (buffers on clock nets), their driver, sink flops, macros -> CSV. env P_ODB P_OUT
read_db $::env(P_ODB)
set blk [ord::get_db_block]; set fo [open $::env(P_OUT) w]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
puts $fo "kind,name,x,y,x2,y2"
lassign [list [[$blk getDieArea] xMax] [[$blk getDieArea] yMax]] dx dy
puts $fo "die,die,0,0,[expr {$dx/double($u)}],[expr {$dy/double($u)}]"
foreach i [$blk getInsts] {
  set m [$i getMaster]
  if {[$m isBlock]} { set b [$i getBBox]; puts $fo "macro,[$i getName],[expr {[$b xMin]/double($u)}],[expr {[$b yMin]/double($u)}],[expr {[$b xMax]/double($u)}],[expr {[$b yMax]/double($u)}]"; continue }
}
foreach bl [$blk getBlockages] { set b [$bl getBBox]; puts $fo "island,blk,[expr {[$b xMin]/double($u)}],[expr {[$b yMin]/double($u)}],[expr {[$b xMax]/double($u)}],[expr {[$b yMax]/double($u)}]" }
foreach bt [$blk getBTerms] { if {[$bt getName] eq "ck"} { set b [$bt getBBox]; puts $fo "ckpin,ck,[expr {[$b xMin]/double($u)}],[expr {[$b yMin]/double($u)}],[expr {[$b xMax]/double($u)}],[expr {[$b yMax]/double($u)}]" } }
foreach n [$blk getNets] {
  if {[$n getSigType] ne "CLOCK"} continue
  set drv ""; foreach it [$n getITerms] { if {[$it isOutputSignal]} { set drv $it } }
  if {$drv eq ""} { set bt [lindex [$n getBTerms] 0]; if {$bt eq ""} continue; set b [$bt getBBox]; set x0 [expr {[$b xMin]/double($u)}]; set y0 [expr {[$b yMin]/double($u)}] } else { lassign [[$drv getInst] getLocation] a b; set x0 [expr {$a/double($u)}]; set y0 [expr {$b/double($u)}] }
  foreach it [$n getITerms] {
    if {[$it isOutputSignal]} continue
    set i [$it getInst]; lassign [$i getLocation] a b
    set k [expr {[string match "*DFF*" [[$i getMaster] getName]] ? "sinkedge" : ([[$i getMaster] isBlock] ? "macroedge" : "bufedge")}]
    puts $fo "$k,[$n getName],$x0,$y0,[expr {$a/double($u)}],[expr {$b/double($u)}]"
  }
}
close $fo; exit
