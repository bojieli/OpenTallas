# Check the exact functional interface. PDN adds POWER/GROUND boxes to the
# same BTerm inventory; those are not RTL ports and are excluded by SigType,
# never by a name prefix. Expected RTL pins classified as PG still fail.
proc ot_ha2_check_signal_identity {expected_names} {
 set b [ord::get_db_block]
 set wanted [dict create]
 foreach name $expected_names {
  if {[dict exists $wanted $name]} {error "duplicate expected truecredit pin $name"}
  dict set wanted $name 1
 }
 set seen [dict create]
 set signal_boxes 0
 set pg_terms 0
 set pg_boxes 0
 set d [$b getDieArea]
 foreach bt [$b getBTerms] {
  set name [$bt getName]
  set type [$bt getSigType]
  if {$type eq "POWER" || $type eq "GROUND"} {
   if {[dict exists $wanted $name]} {error "expected truecredit signal classified $type: $name"}
   incr pg_terms
   foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {incr pg_boxes}}
   continue
  }
  if {![dict exists $wanted $name]} {error "unexpected truecredit signal pin $name"}
  if {[dict exists $seen $name]} {error "duplicate truecredit signal pin $name"}
  dict set seen $name 1
  set boxes 0
  foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {
   incr boxes
   if {[$box xMin]<[$d xMin] || [$box yMin]<[$d yMin] ||
       [$box xMax]>[$d xMax] || [$box yMax]>[$d yMax]} {
    error "truecredit signal box outside die: $name"
   }
  }}
  if {$boxes!=1} {error "truecredit signal $name expected1 box got$boxes"}
  incr signal_boxes $boxes
 }
 foreach name $expected_names {
  if {![dict exists $seen $name]} {error "missing truecredit signal pin $name"}
 }
 if {$signal_boxes!=[llength $expected_names]} {error "truecredit signal box count mismatch"}
 puts "TRUECREDIT_SIGNAL_IDENTITY_PASS signals=$signal_boxes pg_terms=$pg_terms pg_boxes=$pg_boxes"
 return [dict create signals $signal_boxes pg_terms $pg_terms pg_boxes $pg_boxes]
}
