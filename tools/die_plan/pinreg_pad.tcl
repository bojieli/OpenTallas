# GENERATED-COPY of tools/die_plan/pinreg_pad.tcl (FLOW-INFRA-2 2026-10-25, PROTOTYPE for CLOCK-RESET's tap_balance
# items (b)+(d)): bring the boundary pin-register clock mean to the bound insertion on GRT RC by padding ONLY the leaf
# groups that clock pin registers.  Sourced by tapbal_grt.tcl after tap_balance.tcl when OT_PINREG_PAD=1.
# Why: canaries 10-25 (head hd_turn_a tap clk 192..274 ps, KV io_ft trees max 294..315) have pin registers on the
# EARLY side of wide trees; tap_balance pads a whole tree and is capped by its slowest sink (target + window), so it
# adds 0 cells while the pin-register mean (the quantity postcts_gate and the parent contract use) sits 20-25 ps low.
# Pin-register set = postcts_gate.tcl's (registers in the fanout of the data inputs / fanin of the outputs); arrival
# = clock_family.tcl ot_cf_wire (the sign-off clock measure).  Method: group pin-register clock pins by their driving
# leaf net; each iteration the lowest groups (enough to cover the deficit at the measured per-cell step) get one delay
# cell at their sink end (new net, cell at the group centroid, legalised, incremental GRT); stop when the mean is within
# OT_PINREG_PAD_TOL (default 5 ps) or after OT_PINREG_PAD_ITERS (default 6).  Groups above the bound are reported
# (a padding pass cannot trim them: that is a CTS / tap-pitch item).  Interior sinks are never moved.
# Env: OT_VCLK_TT (bound, kit config), OT_PINREG_PAD_CELL (default BUFx2_ASAP7_75t_R).
set pp_bound $::env(OT_VCLK_TT)
set pp_tol [expr {[info exists ::env(OT_PINREG_PAD_TOL)] ? $::env(OT_PINREG_PAD_TOL) : 5.0}]
set pp_iters [expr {[info exists ::env(OT_PINREG_PAD_ITERS)] ? $::env(OT_PINREG_PAD_ITERS) : 6}]
set pp_cell [expr {[info exists ::env(OT_PINREG_PAD_CELL)] ? $::env(OT_PINREG_PAD_CELL) : "BUFx2_ASAP7_75t_R"}]
set pp_blk [ord::get_db_block]
set pp_master [[ord::get_db] findMaster $pp_cell]
if {$pp_master eq "NULL"} { error "OT_PINREG_PAD: no master $pp_cell" }
set pp_clk [get_clocks clk]
set pp_per [get_property $pp_clk period]
# boundary pin registers: the SAME set as postcts_gate.tcl (clock_family.tcl ot_cf_pinregs)
if {![llength [info commands ot_cf_pinregs]]} {
  set pp_cf [file join [file dirname [info script]] clock_family.tcl]
  if {![file exists $pp_cf]} { set pp_cf [file normalize [file join [file dirname [info script]] ../../physical/common_flow/clock_family.tcl]] }
  source $pp_cf
}
set pp_bnd [ot_cf_pinregs]
proc pp_arr {p} {
  global pp_clk pp_per
  return [ot_cf_pinreg_arrival $p $pp_clk $pp_per]
}
# group key = the dbNet driving the pin-register clock iterm (re-read each iteration: padding moves sinks)
proc pp_groups {} {
  global pp_bnd
  set g {}
  dict for {i p} $pp_bnd {
    if {[catch {set it [sta::sta_to_db_pin $p]}] || $it eq "NULL" || $it eq ""} continue
    if {[$it getNet] eq "NULL"} continue
    dict lappend g [[$it getNet] getName] [list $it $p]
  }
  return $g
}
proc pp_measure {} {
  # as tap_balance tb_measure: re-assert propagated clocks (new clock nets/pins), GRT parasitics, fresh timing
  set_propagated_clock [all_clocks]
  estimate_parasitics -global_routing
  catch {sta::worst_slack_cmd max}
  if {[llength [info commands ot_cf_refresh]]} { catch {ot_cf_refresh} }
  set stats {}; set all {}
  dict for {n its} [pp_groups] {
    set s 0.0; set k 0
    foreach ip $its {
      set a [pp_arr [lindex $ip 1]]
      if {![string is double -strict $a]} continue
      set s [expr {$s + $a}]; incr k; lappend all $a
    }
    if {$k} { dict set stats $n [list [expr {$s / $k}] $k $its] }
  }
  set m [expr {[llength $all] ? [tcl::mathop::+ {*}$all] / [llength $all] : -1}]
  return [list $m [llength $all] $stats]
}
# one delay cell at a group's sink end moves that group by ~step ps (BUFx2 driving a ~25-sink leaf: +42 ps measured on
# KV io_ft); each iteration pads only the lowest groups whose predicted shift (pin count x step / all pins) covers the
# deficit, then re-measures and re-estimates step from the padded groups.
set pp_added 0; set pp_seq 0
set pp_step [expr {[info exists ::env(OT_PINREG_PAD_STEP)] ? $::env(OT_PINREG_PAD_STEP) : 40.0}]
set pp_last {}
for {set it 0} {$it <= $pp_iters} {incr it} {
  lassign [pp_measure] m n stats
  set moved {}
  dict for {g v} $pp_last { if {[dict exists $stats $g]} { lappend moved [expr {[lindex [dict get $stats $g] 0] - $v}] } }
  if {[llength $moved]} { set pp_step [expr {max(5.0, [tcl::mathop::+ {*}$moved] / [llength $moved])}] }
  set lo 0; set hi 0
  dict for {g v} $stats { if {[lindex $v 0] < $pp_bound} { incr lo } elseif {[lindex $v 0] > $pp_bound + $pp_tol} { incr hi } }
  puts [format "OT_PINREG_PAD it%d pinreg n %d mean %.2f bound %.2f dev %.2f groups %d (below %d, above %d) step %.1f cells %d" \
    $it $n $m $pp_bound [expr {$m - $pp_bound}] [dict size $stats] $lo $hi $pp_step $pp_added]
  if {$n == 0 || abs($m - $pp_bound) <= $pp_tol || $m > $pp_bound || $it == $pp_iters || $lo == 0} break
  # lowest groups first, until the predicted mean shift covers the deficit
  set need [expr {($pp_bound - $m) * $n}]
  set pick {}; set got 0.0
  set order [lsort -real -index 1 [lmap {g v} $stats {list $g [lindex $v 0]}]]
  foreach e $order {
    lassign $e g gm
    if {$got >= $need || $gm >= $pp_bound} break
    lappend pick $g
    set got [expr {$got + [lindex [dict get $stats $g] 1] * $pp_step}]
  }
  if {![llength $pick]} break
  global_route -start_incremental
  set pp_last {}
  foreach g $pick {
    lassign [dict get $stats $g] gm k its
    set src [[lindex [lindex $its 0] 0] getNet]
    set nn [odb::dbNet_create $pp_blk "ot_prp_n[incr pp_seq]"]
    $nn setSigType CLOCK
    set sx 0; set sy 0
    foreach ip $its { set t [lindex $ip 0]; lassign [[$t getInst] getLocation] x y; set sx [expr {$sx + $x}]; set sy [expr {$sy + $y}]; $t disconnect; $t connect $nn }
    set inst [odb::dbInst_create $pp_blk $pp_master "ot_prp_d$pp_seq"]
    foreach t [$inst getITerms] {
      set mt [$t getMTerm]
      if {[$mt getSigType] in {POWER GROUND}} continue
      if {[$mt getIoType] eq "INPUT"} { $t connect $src } elseif {[$mt getIoType] eq "OUTPUT"} { $t connect $nn }
    }
    $inst setLocation [expr {int($sx / [llength $its])}] [expr {int($sy / [llength $its])}]
    $inst setPlacementStatus PLACED
    dict set pp_last [$nn getName] $gm
    incr pp_added
  }
  detailed_placement
  global_route -end_incremental {*}[expr {[info exists ::ot_grt_res_aware] ? $::ot_grt_res_aware : ""}]
}
puts "OT_PINREG_PAD done: $pp_added delay cells ($pp_cell) on pin-register leaf groups"
