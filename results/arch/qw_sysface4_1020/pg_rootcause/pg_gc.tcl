proc cnt {b} {
  set unb 0; set dnt 0; set dntunb 0
  foreach i [$b getInsts] {
    if {[$i isDoNotTouch]} {incr dnt}
    foreach mt [[$i getMaster] getMTerms] {
      if {[$mt getSigType] ni {POWER GROUND}} continue
      set t [$i findITerm [$mt getName]]
      if {$t eq "NULL" || [$t getNet] eq "NULL"} {incr unb; if {[$i isDoNotTouch]} {incr dntunb}}
    }
  }
  return "unbound=$unb dont_touch_insts=$dnt dont_touch_unbound_terms=$dntunb"
}
foreach f [list $::env(ODB)] {
  read_db $f
  set b [ord::get_db_block]
  puts "PGGC [file tail $f] before: [cnt $b]"
  global_connect
  puts "PGGC [file tail $f] after_global_connect(in-memory, not written): [cnt $b]"
  ord::get_db; # keep
}
