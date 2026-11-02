read_db /input/input.odb
set b [ord::get_db_block]
set f [open /work/db_guides.tsv w]
set p [open /work/pg.tsv w]
foreach n [$b getNets] {
 set ty [$n getSigType]
 if {$ty in {POWER GROUND}} {puts $p "$ty\t[$n getName]\t[$n isSpecial]\t[llength [$n getSWires]]"}
 if {$ty ni {SIGNAL CLOCK}} continue
 foreach g [$n getGuides] {
  set r [$g getBox]
  puts $f "[$n getName]\t[[$g getLayer] getName]\t[$r xMin]\t[$r yMin]\t[$r xMax]\t[$r yMax]"
 }
}
close $f
close $p
write_guides /work/final.route.guide
puts FINAL_GUIDE_WRITE_COMPLETE
