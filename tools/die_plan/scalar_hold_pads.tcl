# Apply only to explicitly named scalar capture D pins. Clock and reset pin nets
# are untouched. The captured signal is delayed by noninverting data buffers.
proc ot_scalar_hold_error {detail} {
  error "OT_SCALAR_HOLD: $detail"
}

proc ot_scalar_hold_routes {net goal mode remaining seen} {
  if {$net eq "NULL" || $remaining < 0 || $net in $seen} {return 0}
  set n 0
  foreach bt [$net getBTerms] {
    if {$bt eq $goal} {incr n}
  }
  foreach it [$net getITerms] {
    if {![$it isOutputSignal]} {continue}
    set i [$it getInst]
    set master [[$i getMaster] getName]
    if {$mode eq "buffer" && ![regexp {^(BUF|HB)} $master]} {continue}
    if {$mode eq "comb" && ![regexp {^(BUF|HB|INV|AND|NAND|AO|OA|OR|NOR|XNOR|XOR|MAJ)} $master]} {continue}
    foreach input [$i getITerms] {
      if {![$input isInputSignal] || [[$input getMTerm] getSigType] ne "SIGNAL"} {continue}
      incr n [ot_scalar_hold_routes [$input getNet] $goal $mode [expr {$remaining-1}] [linsert $seen end $net]]
    }
  }
  return $n
}

proc ot_scalar_hold_before {block row} {
  lassign $row port endpoint count mode
  set bt [$block findBTerm $port]
  if {$bt eq "NULL" || [$bt getIoType] ne "INPUT" || [$bt getSigType] ne "SIGNAL"} {
    ot_scalar_hold_error "missing scalar SIGNAL input $port"
  }
  set ff [$block findInst $endpoint]
  if {$ff eq "NULL" || [[$ff getMaster] getName] ne "DFFHQNx1_ASAP7_75t_R"} {
    ot_scalar_hold_error "uncharacterized capture $endpoint"
  }
  set d [$ff findITerm D]
  set n [$d getNet]
  if {$n eq "NULL" || [$n isSpecial] || [$n getSigType] ne "SIGNAL"} {
    ot_scalar_hold_error "uncharacterized capture net $endpoint/D"
  }
  set drivers 0
  foreach term [$n getITerms] {
    if {[$term isOutputSignal]} {incr drivers}
  }
  foreach external [$n getBTerms] {
    if {[$external getIoType] eq "INPUT"} {incr drivers}
  }
  if {$drivers != 1} {ot_scalar_hold_error "capture branch lacks a unique driver for $endpoint/D"}
  if {[ot_scalar_hold_routes $n $bt $mode 7 {}] != 1} {
    ot_scalar_hold_error "missing or ambiguous original path $port to $endpoint/D"
  }
  return [list $ff $d $n]
}

proc ot_scalar_hold_insert {} {
  set block [ord::get_db_block]
  set master [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
  if {$master eq "NULL"} {ot_scalar_hold_error "HB4 master missing"}
  set width [$master getWidth]
  set core [$block getCoreArea]
  set checked {}
  foreach row $::ot_scalar_hold_pads {
    lassign $row port endpoint count mode
    lassign [ot_scalar_hold_before $block $row] ff d net
    lassign [$ff getLocation] x y
    set left [expr {$x-$count*$width}]
    if {$left < [$core xMin]} {set left [expr {$x+[[$ff getMaster] getWidth]}]}
    if {$left < [$core xMin] || $left+$count*$width > [$core xMax]} {
      ot_scalar_hold_error "no near-capture seed for $endpoint"
    }
    for {set i 0} {$i < $count} {incr i} {
      set name "ot_scalar_hold_${port}_$i"
      if {[$block findInst $name] ne "NULL" || [$block findNet "${name}_n"] ne "NULL"} {
        ot_scalar_hold_error "duplicate instance or net $name"
      }
    }
    lappend checked [list $port $count $ff $d $net $left $y]
  }

  set pads {}
  set names {}
  set nets {}
  foreach e $checked {
    lassign $e port count ff d net x y
    $d disconnect
    for {set i 0} {$i < $count} {incr i} {
      set name "ot_scalar_hold_${port}_$i"
      set pad [odb::dbInst_create $block $master $name]
      set next [odb::dbNet_create $block "${name}_n"]
      [$pad findITerm A] connect $net
      [$pad findITerm Y] connect $next
      $pad setOrient [$ff getOrient]
      $pad setLocation [expr {$x+$i*$width}] $y
      $pad setPlacementStatus PLACED
      lappend pads $pad
      lappend names $name
      lappend nets $next
      set net $next
    }
    $d connect $net
  }
  source /work/native_pg_binding.tcl
  set pg [ot_pg_bind_batch_before_protect $block $pads]
  set_dont_touch [get_cells $names]
  foreach net $nets {$net setDoNotTouch 1}
  puts "OT_SCALAR_HOLD inserted [llength $pads] data pads, native PG bound $pg"
}

proc ot_scalar_hold_check {} {
  set block [ord::get_db_block]
  set dbu [$block getDbUnitsPerMicron]
  set total 0
  set max_leg 0
  foreach row $::ot_scalar_hold_pads {
    lassign $row port endpoint count mode
    set bt [$block findBTerm $port]
    set ff [$block findInst $endpoint]
    if {$bt eq "NULL" || $ff eq "NULL"} {ot_scalar_hold_error "pad endpoints changed for $port"}
    set next [[$ff findITerm D] getNet]
    lassign [$ff getLocation] nx ny
    for {set i [expr {$count-1}]} {$i >= 0} {incr i -1} {
      set pad [$block findInst "ot_scalar_hold_${port}_$i"]
      if {$pad eq "NULL" || [[$pad getMaster] getName] ne "HB4xp67_ASAP7_75t_R" ||
          [[$pad findITerm Y] getNet] ne $next || ![$pad isPlaced]} {
        ot_scalar_hold_error "missing, changed or unplaced pad for $port index $i"
      }
      if {[llength [$next getITerms]] != 2 || [llength [$next getBTerms]] != 0} {
        ot_scalar_hold_error "pad chain changed fanout for $port index $i"
      }
      lassign [$pad getLocation] px py
      set length [expr {(abs($px-$nx)+abs($py-$ny))/double($dbu)}]
      set max_leg [expr {max($max_leg, $length)}]
      if {$length > 5.0} {ot_scalar_hold_error "pad hop $length um exceeds 5 um for $port index $i"}
      set next [[$pad findITerm A] getNet]
      lassign [list $px $py] nx ny
      incr total
    }
    if {[ot_scalar_hold_routes $next $bt $mode 7 {}] != 1} {
      ot_scalar_hold_error "original input driver changed for $port"
    }
  }
  puts [format "OT_SCALAR_HOLD checked %d data pads, max local hop %.3f um" $total $max_leg]
}
