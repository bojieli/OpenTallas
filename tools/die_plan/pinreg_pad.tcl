# GENERATED-COPY of tools/die_plan/pinreg_pad.tcl (FLOW-INFRA-2 2026-10-25, PROTOTYPE for CLOCK-RESET's tap_balance
# items (b)+(d)): bring the boundary pin-register clock mean to the bound insertion on GRT RC by padding ONLY the leaf
# groups that clock pin registers.  Sourced by tapbal_grt.tcl after tap_balance.tcl when OT_PINREG_PAD=1.
# Why: canaries 10-25 (head hd_turn_a tap clk 192..274 ps, KV io_ft trees max 294..315) have pin registers on the
# EARLY side of wide trees; tap_balance pads a whole tree and is capped by its slowest sink (target + window), so it
# adds 0 cells while the pin-register mean (the quantity postcts_gate and the parent contract use) sits 20-25 ps low.
# Pin-register set = postcts_gate.tcl's (registers in the fanout of the data inputs / fanin of the outputs); arrival
# = clock_family.tcl ot_cf_wire (the sign-off clock measure).  Method: group pin-register clock pins by their driving
# leaf net; each iteration, every group whose GRT mean is below bound - step/2 gets one delay cell at its sink end
# (new net, cell at the group centroid, legalised, incremental GRT); stop when the overall mean is within
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
# boundary pin registers (postcts_gate.tcl set)
set pp_regs {}
foreach p [all_registers -clock_pins] { dict set pp_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set pp_bnd {}
set pp_din [all_inputs -no_clocks]
if {[llength $pp_din]} {
  foreach p [get_fanout -from $pp_din -flat -endpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $pp_regs $i]} { dict set pp_bnd $i 1 }
  }
}
if {[llength [all_outputs]]} {
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $pp_regs $i]} { dict set pp_bnd $i 1 }
  }
}
proc pp_arr {p} {
  global pp_clk pp_per
  set a ""
  if {[llength [info commands ot_cf_wire]]} { catch {set a [ot_cf_wire $p $pp_clk]} }
  if {$a eq ""} {
    if {[catch {set a [get_property $p arrival_max_rise]}]} { return "" }
    if {[string is double -strict $a] && $a >= $pp_per / 2.0 && $a < $pp_per} { set a [expr {$a - $pp_per / 2.0}] }
  }
  return $a
}
# group key = the dbNet driving the pin-register clock iterm (re-read each iteration: padding moves sinks)
proc pp_groups {} {
  global pp_bnd pp_regs
  set g {}
  dict for {i u} $pp_bnd {
    set p [dict get $pp_regs $i]
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
set pp_added 0; set pp_step 12.0; set pp_seq 0
for {set it 0} {$it <= $pp_iters} {incr it} {
  lassign [pp_measure] m n stats
  set lo 0; set hi 0
  dict for {g v} $stats { if {[lindex $v 0] < $pp_bound - $pp_step / 2.0} { incr lo } elseif {[lindex $v 0] > $pp_bound + $pp_tol} { incr hi } }
  puts [format "OT_PINREG_PAD it%d pinreg n %d mean %.2f bound %.2f dev %.2f groups %d (below %d, above %d) cells %d" \
    $it $n $m $pp_bound [expr {$m - $pp_bound}] [dict size $stats] $lo $hi $pp_added]
  if {$n == 0 || $m >= $pp_bound - $pp_tol || $it == $pp_iters || $lo == 0} break
  global_route -start_incremental
  set made 0
  dict for {g v} $stats {
    lassign $v gm k its
    if {$gm >= $pp_bound - $pp_step / 2.0} continue
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
    incr made
  }
  detailed_placement
  global_route -end_incremental
  incr pp_added $made
}
puts "OT_PINREG_PAD done: $pp_added delay cells ($pp_cell) on pin-register leaf groups"
