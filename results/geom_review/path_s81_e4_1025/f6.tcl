# F6: per ROM bank, Manhattan distance capture flop (bank_words) -> the ROM rd pin feeding its D cone
read_db $::env(ODB)
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
proc drv {n} { foreach it [$n getITerms] { if {[$it isOutputSignal]} { return $it } }; return "" }
proc findrom {net d} {
  set it [drv $net]; if {$it eq ""} { return "" }
  set i [$it getInst]
  if {[[$i getMaster] isBlock]} { return $it }
  if {$d <= 0 || [[$i getMaster] isSequential]} { return "" }
  foreach t [$i getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { set r [findrom [$t getNet] [expr {$d-1}]]; if {$r ne ""} { return $r } } }
  return ""
}
set fh [open $::env(OUT) w]
puts $fh "flop\tword\trom\tdist_um\tfx\tfy\tpx\tpy"
foreach i [$b getInsts] {
  set n [$i getName]
  if {![regexp {bank_words\\?\[(\d+)\\?\]} $n -> k]} continue
  set r [findrom [[$i findITerm D] getNet] 4]
  if {$r eq ""} { puts $fh "$n\t$k\tNONE\t-1\t0\t0\t0\t0"; continue }
  set pb [$r getBBox]; set px [expr {([$pb xMin]+[$pb xMax])/2.0/$u}]; set py [expr {([$pb yMin]+[$pb yMax])/2.0/$u}]
  set ib [$i getBBox]; set fx [expr {([$ib xMin]+[$ib xMax])/2.0/$u}]; set fy [expr {([$ib yMin]+[$ib yMax])/2.0/$u}]
  puts $fh [format "%s\t%d\t%s\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f" $n $k [[$r getInst] getName] [expr {abs($fx-$px)+abs($fy-$py)}] $fx $fy $px $py]
}
close $fh
puts "F6 done"
