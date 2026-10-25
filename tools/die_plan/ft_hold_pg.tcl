# Deterministic hold cells stay dont_touch through optimization. OpenDB global_connect skips dont_touch instances,
# so connect their real power/ground ITerms explicitly after PDN creation, before placement.
set fhp_blk [ord::get_db_block]
set fhp_n 0
foreach fhp_i [$fhp_blk getInsts] {
  if {![string match {u_ftd_*} [$fhp_i getName]]} continue
  set fhp_keep [$fhp_i isDoNotTouch]
  $fhp_i setDoNotTouch false
  foreach fhp_it [$fhp_i getITerms] {
    set fhp_mt [$fhp_it getMTerm]
    if {[$fhp_mt getSigType] ni {POWER GROUND}} continue
    set fhp_net [$fhp_blk findNet [$fhp_mt getName]]
    if {$fhp_net eq "NULL" || $fhp_net eq ""} { error "OT_FT_HOLD_PG missing supply net [$fhp_mt getName]" }
    $fhp_it connect $fhp_net
    incr fhp_n
  }
  $fhp_i setDoNotTouch $fhp_keep
}
puts "OT_FT_HOLD_PG connected $fhp_n power/ground terminals (delay cells remain dont_touch)"
