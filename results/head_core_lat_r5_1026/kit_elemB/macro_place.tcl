# HEAD-CORE-LAT-R5 PLAN-DELTA probe (same as elemA_n50): ROMs moved from the centre pair to the N band side by side
# (gap 8.64 at the core centre x 142.56), so the centre entry (142.56,142.56) sees the logic without a ROM in between.
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach {name x y orient} {u_m.u_rom0 12.96 211.68 MY u_m.u_rom1 146.88 211.68 MY} {
  set i [$b findInst $name]
  if {$i eq "NULL" || $i eq ""} { error "R5 macro_place: no instance $name" }
  $i setOrient $orient
  $i setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]
  $i setPlacementStatus FIRM
  puts "R5 place: $name at $x $y $orient"
}
