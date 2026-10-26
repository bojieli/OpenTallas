set b [ord::get_db_block]
set n 0
set ff 0
foreach i [$b getInsts] {
 if {![string match DFF* [[$i getMaster] getName]]} continue
 incr ff
 $i setDoNotTouch false
 foreach t [$i getITerms] {
  set st [[$t getMTerm] getSigType]
  if {$st ne "POWER" && $st ne "GROUND"} continue
  set rail [expr {$st eq "POWER" ? "VDD" : "VSS"}]
  set net [$b findNet $rail]
  if {$net eq "NULL" || $net eq ""} {error "missing $rail"}
  $t connect $net
  if {[$t getNet] ne $net} {error "PG connect failed"}
  incr n
 }
 $i setDoNotTouch true
}
if {$ff != 12030 || $n != 24060} {error "FF/PG cohort changed: $ff/$n"}
puts "NATIVE_FF_PG preserved $ff FF, explicitly connected $n PG terminals"
