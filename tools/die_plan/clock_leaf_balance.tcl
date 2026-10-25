# Opt-in local CTS direct clock-sink group balancing for a single-clock hard core.
# Preserve the clock entry, polarity, sink ownership and SDC. Delay early terminal
# clock-sink groups (never data pins) rather than padding the entire tree.
# Call after CTS, or after GRT with CQB_GRT=1; route and signoff remain mandatory.
source /work/clock_family.tcl
proc cqb_measure {} {
  set_propagated_clock [all_clocks]
  if {[info exists ::env(CQB_GRT)] && $::env(CQB_GRT)} {
    estimate_parasitics -global_routing
  } else { estimate_parasitics -placement }
  ot_cf_refresh
  set groups {}
  foreach pin [all_registers -clock_pins] {
    set clocks [get_property $pin clocks]
    if {[llength $clocks] != 1} { error "CQB ambiguous sink [get_full_name $pin]" }
    set name [get_full_name $pin]
    set it [[ord::get_db_block] findITerm $name]
    if {$it eq "NULL"} {
      set it [[ord::get_db_block] findITerm [string map [list {[} {\[} {]} {\]}] $name]]
    }
    if {$it eq "NULL"} {error "CQB clock sink has no OpenDB pin: $name"}
    set net [$it getNet]
    if {$net eq "NULL"} {error "CQB unconnected clock sink: $name"}
    dict lappend groups [$net getName] [list [ot_cf_wire $pin [lindex $clocks 0]] $it]
  }
  puts "CQB coverage [llength [all_registers -clock_pins]] clock pins / [dict size $groups] direct-sink groups"
  set out {}
  dict for {nn vals} $groups {
    set net [[ord::get_db_block] findNet $nn]
    # A clock net may drive both registers and deeper CTS buffers. Rehang
    # only its measured clock sinks, leaving all downstream CTS branches alone.
    set inputs {}; set arrivals {}
    foreach row $vals {lappend arrivals [lindex $row 0]; lappend inputs [lindex $row 1]}
    set vals $arrivals
    set vals [lsort -real $vals]; set sum 0
    foreach a $vals {set sum [expr {$sum+$a}]}
    dict set out $nn [list $inputs [expr {$sum/[llength $vals]}] [lindex $vals 0] [lindex $vals end] [llength $vals]]
  }
  return $out
}
proc cqb_hang {inputs n tag} {
  set blk [ord::get_db_block]; set master [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
  if {$master eq "NULL"} {error "CQB missing delay cell"}
  set input [lindex $inputs 0]
  set original [$input getNet]
  set bb [[$input getInst] getBBox]
  set x [$bb xMin]; set y [$bb yMin]
  foreach input $inputs {$input disconnect}
  set prev $original
  for {set i 0} {$i<$n} {incr i} {
    set net [odb::dbNet_create $blk "${tag}_n$i"]; $net setSigType CLOCK
    set buf [odb::dbInst_create $blk $master "${tag}_b$i"]
    foreach it [$buf getITerms] {
      set mt [$it getMTerm]
      if {[$mt getSigType] in {POWER GROUND}} continue
      if {[$mt getIoType] eq "INPUT"} {$it connect $prev} elseif {[$mt getIoType] eq "OUTPUT"} {$it connect $net}
    }
    $buf setLocation [expr {$x+$i*2*[$master getWidth]}] $y
    $buf setPlacementStatus PLACED
    set prev $net
  }
  foreach input $inputs {$input connect $prev}
}
set cqb_prefix [expr {[info exists ::env(CQB_TAG)] ? $::env(CQB_TAG) : "cqb"}]
set cqb_added 0
for {set cqb_iter 0} {$cqb_iter<3} {incr cqb_iter} {
  set cqb_m [cqb_measure]
  if {![dict size $cqb_m]} {error "CQB no direct clock-sink groups"}
  set target -1e9; set min 1e9; set max -1e9
  dict for {nn row} $cqb_m {
    set target [expr {max($target,[lindex $row 1])}]
    set min [expr {min($min,[lindex $row 2])}]
    set max [expr {max($max,[lindex $row 3])}]
  }
  puts "CQB iter$cqb_iter branches[dict size $cqb_m] sink_range $min $max mean_target $target"
  if {$cqb_iter==0} {set cqb_target [expr {$target-10.0}]}
  set todo {}; set cqb_count 0
  dict for {nn row} $cqb_m {
    lassign $row input mean low high count
    set delay [expr {min(75.0,$cqb_target-$mean,$cqb_target+20.0-$high)}]
    if {$delay<=15.0} continue
    set n [expr {max(1,int(round($delay/18.0*0.65)))}]
    lappend todo [list $input $n "${cqb_prefix}_${cqb_iter}_$cqb_count"]
    incr cqb_count; incr cqb_added $n
  }
  if {![llength $todo]} break
  if {[info exists ::env(CQB_GRT)] && $::env(CQB_GRT)} {global_route -start_incremental}
  foreach row $todo {cqb_hang {*}$row}
  detailed_placement
  if {[info exists ::env(CQB_GRT)] && $::env(CQB_GRT)} {global_route -end_incremental}
}
puts "CQB done buffers$cqb_added (clock only; measured signoff required)"
