# Remove only one-input transparent cells with no remaining signal loads or
# observable port. This is logical dead-path pruning, never a dummy load.
set ot_pruned {}
set ot_prune_changed 1
while {$ot_prune_changed} {
 set ot_prune_changed 0
 foreach inst [[ord::get_db_block] getInsts] {
  set master [$inst getMaster];set mn [$master getName]
  if {[$master isSequential] || [$master isBlock]} continue
  if {![string match BUF* $mn] && ![string match *INV* $mn] && $mn ni {HB2xp67_ASAP7_75t_R HB4xp67_ASAP7_75t_R}} continue
  set observable 0;set outs 0
  foreach t [$inst getITerms] {
   if {![$t isOutputSignal]} continue
   incr outs;set net [$t getNet]
   if {$net eq "NULL" || $net eq ""} continue
   if {[llength [$net getBTerms]]} {set observable 1;break}
   foreach load [$net getITerms] {if {[$load isInputSignal]} {set observable 1;break}}
  }
  if {$observable || $outs!=1} continue
  lappend ot_pruned [list [$inst getName] $mn]
  # Preserve flags on retained original nets; destroyed cells have no observable output.
  if {[$inst isDoNotTouch]} {$inst setDoNotTouch false}
  set nets {}
  foreach t [$inst getITerms] {
   set net [$t getNet]
   if {$net eq "NULL" || $net eq ""} continue
   if {[$net isDoNotTouch]} {dict set nets $net 1;$net setDoNotTouch false}
   $t disconnect
  }
  foreach net [dict keys $nets] {$net setDoNotTouch true}
  odb::dbInst_destroy $inst
  set ot_prune_changed 1
 }
}
puts "UNOBSERVED_TRANSPARENT_PRUNE count=[llength $ot_pruned] no_observable_port_or_signal_load_at_removal=1"
if {[info exists ::ot_prune_manifest]} {set f [open $::ot_prune_manifest w];puts $f [list set ::ot_pruned $ot_pruned];close $f}
