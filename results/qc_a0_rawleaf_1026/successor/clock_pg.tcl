# Connect the actual newly inserted CTS cells before judging pre-route PDN.
# Keep the original checkpoint immutable. No placement or signal nets change.
read_db $::env(ODB)
set b [ord::get_db_block]
set count 0;set bad_before 0;set fixed 0;set dnt 0
foreach i [$b getInsts] {
 if {![string match clkbuf* [$i getName]]} continue
 incr count
 set keep [$i isDoNotTouch]
 if {$keep} {incr dnt;$i setDoNotTouch false}
 foreach t [$i getITerms] {
  set st [[$t getMTerm] getSigType]
  if {$st ni {POWER GROUND}} continue
  set name [expr {$st eq "POWER" ? "VDD" : "VSS"}]
  set n [$b findNet $name]
  if {$n eq "NULL" || $n eq ""} {error "missing existing $name rail"}
  if {[$t getNet] ne $n} {incr bad_before;$t connect $n;incr fixed}
  if {[$t getNet] ne $n} {error "CTS PG connect failed"}
 }
 if {$keep} {$i setDoNotTouch true}
}
if {$count != 567 || $fixed != 1134} {error "unexpected actual CTS cohort: $count/$fixed"}
puts "A0_CTS_PG_FIX buffers $count DNT $dnt bad_before $bad_before fixed $fixed bad_after 0"
write_db $::env(OUT_ODB)
exit
