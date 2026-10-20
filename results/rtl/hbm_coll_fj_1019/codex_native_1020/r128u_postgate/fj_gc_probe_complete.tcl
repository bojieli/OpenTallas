set originals {};set f [open $::env(ORIGINAL_NAMES) r];while {[gets $f n]>=0} {dict set originals $n 1};close $f
read_db $::env(AUDIT_ODB)
proc counts {originals} {
 set b [ord::get_db_block];set c {};set protection {}
 foreach i [$b getInsts] {
  set name [$i getName];set dt [$i isDoNotTouch];set fixed [$i isFixed];dict set protection $name [list $dt [$i getPlacementStatus]]
  set origin [expr {[dict exists $originals $name]?"original":"newborn"}]
  dict incr c [list instances $origin protected$dt fixed$fixed]
  foreach t [$i getITerms] {
   if {[$t getSigType] ni {POWER GROUND}} continue
   set n [$t getNet];if {$n eq "NULL" || $n eq ""} {dict incr c [list unbound_iterms $origin protected$dt fixed$fixed]}
  }
 }
 return [list $c $protection]
}
lassign [counts $originals] before protection
puts "FJ_GC_BEFORE $before"
global_connect
lassign [counts $originals] after protection_after
puts "FJ_GC_AFTER $after"
puts "FJ_GC_PROTECTION_UNCHANGED [expr {$protection eq $protection_after}]"
