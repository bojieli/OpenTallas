proc oh_pins {} {
 set d {};foreach bt [[ord::get_db_block] getBTerms] {
  set v [list [$bt getIoType] [$bt getSigType]]
  foreach bp [$bt getBPins] {foreach r [$bp getBoxes] {lappend v [list [[$r getTechLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]}}
  dict set d [$bt getName] $v
 };return $d
}
proc oh_pg_wires {} {
 set d {};foreach n [[ord::get_db_block] getNets] {
  if {[$n getSigType] ni {POWER GROUND}} continue
  set v {};foreach sw [$n getSWires] {foreach r [$sw getWires] {
   if {[$r isVia]} {set ty VIA} else {set ty [[$r getTechLayer] getName]}
   lappend v [list $ty [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
  }};dict set d [$n getName] [lsort $v]
 };return $d
}
