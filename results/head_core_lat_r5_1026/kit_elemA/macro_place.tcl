# HEAD-CORE-LAT-R5 PLAN-DELTA probe (12.7/12.8b, COORD RULING HEAD-CORE-LAT-R4 step 2): ROMs moved from the centre pair
# (95.04,86.40)/(95.04,172.80) to the N band side by side, so the centre entry (159.84,159.84) sees the logic without a ROM
# between them (R4/R5 root cause: 4.5k sinks behind u_rom0). Geometry probe (synth netlist unchanged, place only).
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
foreach {name x y orient} {u_m.u_rom0 30.24 246.24 R0 u_m.u_rom1 164.16 246.24 R0} {
  set i [$b findInst $name]
  if {$i eq "NULL" || $i eq ""} { error "R5 macro_place: no instance $name" }
  $i setOrient $orient
  $i setLocation [expr {round($x * $dbu)}] [expr {round($y * $dbu)}]
  $i setPlacementStatus FIRM
  puts "R5 place: $name at $x $y $orient"
}
