# E5 planned clock buffer islands in NEW legal rows between SRAM macro halos.
# Reserved before GPL, released before CTS; same F6 netlist and all boundary pins.
proc ot_e5_clock_islands {mode} {
  set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
  set boxes {}
  foreach y {258.12 353.16} {
    foreach x {237.06 312.12} {
      lappend boxes [list [expr {round($x*$u)}] [expr {round($y*$u)}] [expr {round(($x+5.94)*$u)}] [expr {round(($y+4.32)*$u)}]]
    }
  }
  if {$mode eq "reserve"} {
    foreach box $boxes {odb::dbBlockage_create $b {*}$box}
    puts "E5_CLOCK_ISLANDS reserved4x5.94x4.32um clockonly white-space islands"
  } elseif {$mode eq "release"} {
    set n 0
    foreach bb [$b getBlockages] {
      set r [$bb getBBox];set box [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
      if {$box in $boxes} {odb::dbBlockage_destroy $bb;incr n}
    }
    if {$n != 4} {error "E5 clock island release expected4 exact planned blocks, found$n"}
    puts "E5_CLOCK_ISLANDS released4 blocks beforeclockcells; no data instance moved"
  } else {error "unknown E5 clockislandphase"}
}
