read_db /work/4_cts.odb
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set f [open /work/rm_pg_shapes.tsv w];puts $f "net\tkind\tlayer\tx0\ty0\tx1\ty1";set count 0
foreach n [$b getNets] {
 if {![$n isSpecial] || [$n getSigType] ni {POWER GROUND}} continue
 foreach sw [$n getSWires] {foreach s [$sw getWires] {
  if {[$s xMin]>2920*$u || [$s xMax]<1350*$u || [$s yMin]>450*$u || [$s yMax]<0} continue
  if {[$s isVia]} {
   set v [$s getTechVia];if {$v eq "NULL"} {set v [$s getBlockVia]};if {$v eq "NULL"} continue
   set layer "[[$v getBottomLayer] getName]-[[$v getTopLayer] getName]";set kind via
  } else {set l [$s getTechLayer];if {$l eq "NULL"} continue;set layer [$l getName];set kind wire}
  if {$layer in {M1 M2 M1-M2}} continue
  puts $f [join [list [$n getName] $kind $layer [expr {double([$s xMin])/$u}] [expr {double([$s yMin])/$u}] [expr {double([$s xMax])/$u}] [expr {double([$s yMax])/$u}]] "\t"];incr count
 }}
}
close $f;puts "RM_ACTUAL_PG_SHAPES $count; region1350..2920x0..450; M1/M2followrails omitted; noODBmutation"
exit
