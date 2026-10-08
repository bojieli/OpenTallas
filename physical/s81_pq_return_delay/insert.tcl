# Explicit identity cells on the source-pinned return endpoints. This file never
# reads/writes the baseline ODB and never changes timing constraints.
# pq_delay_plan entries: {capture_instance D driver_instance driver_pin original_net cells}
proc pq_delay_required {obj label} {
  if {$obj eq "NULL" || $obj eq ""} { error "PQ_DELAY missing $label" }
  return $obj
}
proc pq_delay_check_original {} {
  set b [ord::get_db_block]
  foreach row $::pq_delay_plan {
    lassign $row endpoint dp driver op netname count
    if {$count ni {3 4}} { error "PQ_DELAY unmodeled chain length" }
    set ff [pq_delay_required [$b findInst $endpoint] $endpoint]
    set d [pq_delay_required [$ff findITerm $dp] $endpoint/$dp]
    set source [pq_delay_required [$b findInst $driver] $driver]
    set y [pq_delay_required [$source findITerm $op] $driver/$op]
    set net [pq_delay_required [$b findNet $netname] $netname]
    if {[[$ff getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R" || [[$source getMaster] getName] ne "BUFx2_ASAP7_75t_R"} { error "PQ_DELAY uncharacterized driver/capture" }
    if {[$d getNet] ne $net || [$y getNet] ne $net || [llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0} { error "PQ_DELAY original endpoint/driver topology differs" }
  }
}
proc pq_delay_apply {} {
  pq_delay_check_original
  set b [ord::get_db_block]; set db [ord::get_db]
  set master [pq_delay_required [$db findMaster HB4xp67_ASAP7_75t_R] HB4]
  set idx 0
  foreach row $::pq_delay_plan {
    lassign $row endpoint dp driver op netname count
    set ff [$b findInst $endpoint]; set d [$ff findITerm $dp]
    lassign [$ff getLocation] x y
    set width [$master getWidth]
    set core [$b getCoreArea]
    set start_x [expr {$x-$count*$width}]
    if {$start_x<[$core xMin]} { set start_x [expr {$x+[[$ff getMaster] getWidth]}] }
    if {$start_x+$count*$width>[$core xMax]} { error "PQ_DELAY local seed cannot fit core" }
    set previous [$b findNet $netname]
    $d disconnect
    for {set k 0} {$k<$count} {incr k} {
      set name [format "pq_return_hold_e%05d_s%d" $idx $k]
      set nn [format "pq_return_hold_e%05d_n%d" $idx $k]
      if {[$b findInst $name] ne "NULL" || [$b findNet $nn] ne "NULL"} { error "PQ_DELAY refusing duplicate insertion" }
      set cell [odb::dbInst_create $b $master $name]
      set net [odb::dbNet_create $b $nn]
      [$cell findITerm A] connect $previous
      [$cell findITerm Y] connect $net
      # Legalization is mandatory after this near-capture seed placement.
      $cell setOrient [$ff getOrient]
      $cell setLocation [expr {$start_x+$k*$width}] $y
      $cell setPlacementStatus PLACED
      set previous $net
    }
    $d connect $previous
    incr idx
  }
  set_dont_touch [get_cells pq_return_hold_*]
  pq_delay_check 0
}
proc pq_delay_check {{check_span 1}} {
  set b [ord::get_db_block];set idx 0;set expected 0
  set units [$b getDbUnitsPerMicron]
  foreach row $::pq_delay_plan {
    lassign $row endpoint dp driver op netname count
    set ff [pq_delay_required [$b findInst $endpoint] $endpoint]
    set d [pq_delay_required [$ff findITerm $dp] $endpoint/$dp]
    set source [pq_delay_required [$b findInst $driver] $driver]
    set previous [pq_delay_required [$b findNet $netname] $netname]
    if {[[$source getMaster] getName] ne "BUFx2_ASAP7_75t_R" || [[$ff getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} { error "PQ_DELAY driver/capture master changed" }
    if {[[$source findITerm $op] getNet] ne $previous} { error "PQ_DELAY original driver was changed" }
    set prior_cell $source
    for {set k 0} {$k<$count} {incr k} {
      set name [format "pq_return_hold_e%05d_s%d" $idx $k]
      set cell [pq_delay_required [$b findInst $name] $name]
      set next [pq_delay_required [$b findNet [format "pq_return_hold_e%05d_n%d" $idx $k]] chain_net]
      if {[[$cell getMaster] getName] ne "HB4xp67_ASAP7_75t_R" || [[$cell findITerm A] getNet] ne $previous || [[$cell findITerm Y] getNet] ne $next} { error "PQ_DELAY chain cell/connectivity differs" }
      if {[llength [$previous getITerms]] != 2 || [llength [$previous getBTerms]] != 0} { error "PQ_DELAY chain acquired fanout or lost connectivity" }
      if {$check_span && $k>0} { pq_delay_span $prior_cell $cell $units }
      set previous $next;set prior_cell $cell;incr expected
    }
    if {[$d getNet] ne $previous || [llength [$previous getITerms]] != 2 || [llength [$previous getBTerms]] != 0} { error "PQ_DELAY capture/tag alignment differs" }
    if {$check_span} { pq_delay_span $prior_cell $ff $units }
    incr idx
  }
  set actual 0
  foreach cell [$b getInsts] { if {[string match pq_return_hold_* [$cell getName]]} { incr actual } }
  if {$actual!=$expected} { error "PQ_DELAY actual cell count $actual != modeled $expected" }
  puts "PQ_DELAY_TOPOLOGY_PASS endpoints=$idx cells=$expected placement_checked=$check_span"
}
proc pq_delay_span {a b units} {
  # The pre-existing driver-to-first-cell link is retained separately.
  # Rect-centre Manhattan span is only a placement gate; the final extracted
  # wire capacitance <=0.78fF per chain link is a separate mandatory gate.
  set aa [$a getBBox];set bb [$b getBBox]
  set d [expr {(abs(([$aa xMin]+[$aa xMax])-([$bb xMin]+[$bb xMax]))+abs(([$aa yMin]+[$aa yMax])-([$bb yMin]+[$bb yMax])))/(2.0*$units)}]
  if {$d>5.0} { error "PQ_DELAY link span $d um exceeds modeled 5um" }
}
