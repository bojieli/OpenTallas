read_db /base/4_1_cts.odb

set pg 0;set unbound 0;set protected 0;set fixed 0;set both 0
set fp [open /out/4_1_cts.tsv w]
puts $fp "instance\tmaster\tpin\tdont_touch\tfixed\tplacement"
foreach inst [[ord::get_db_block] getInsts] {
 foreach it [$inst getITerms] {
  if {[$it getSigType] ni {POWER GROUND}} {continue}
  incr pg
  if {[$it getNet] ne "NULL"} {continue}
  incr unbound
  set dt [$inst isDoNotTouch];set fx [$inst isFixed]
  if {$dt} {incr protected};if {$fx} {incr fixed};if {$dt && $fx} {incr both}
  puts $fp "[$inst getName]\t[[$inst getMaster] getName]\t[[$it getMTerm] getName]\t$dt\t$fx\t[$inst getPlacementStatus]"
 }
}
close $fp
puts "OT_PG_STATE total=$pg unbound=$unbound protected_unbound=$protected fixed_unbound=$fixed both=$both"
exit
