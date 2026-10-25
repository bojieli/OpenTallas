# Opt-in local CTS direct clock-sink group balancing for a single-clock hard core.
# Preserve the clock entry, polarity, sink ownership and SDC. Delay early terminal
# clock-sink groups (never data pins) rather than padding the entire tree.
# Call after CTS, or after GRT with CQB_GRT=1; route and signoff remain mandatory.
# QC rp1-clock 10-25 (opt-in knobs; defaults reproduce the codex 67860d0a3 behaviour exactly):
#   CQB_OFF   target = (latest direct-sink group mean) - CQB_OFF            (default 10 ps)
#   CQB_WIN   a delayed group's latest sink may end at most CQB_WIN past the target (default 20 ps)
#   CQB_CAP   max delay added to one group per iteration                    (default 75 ps)
#   CQB_ITERS balancing iterations                                          (default 3)
#   CQB_SPLIT 1 = within each direct-sink group delay only the sinks that arrive before target - CQB_WIN/2,
#             so a group whose own sinks straddle the window is pulled into a CQB_WIN window too (default 0)
#   CQB_MACRO_SAFE 1 = a delay chain feeding a macro clock pin is seeded just outside the macro outline (on the
#             side nearest the pin) instead of at the macro origin, so no clock buffer lands inside a macro outline
#             before legalisation (GEOM qc_clock_1025 PASS-COND condition) (default 0)
# QC-RP1 10-25: ORFS runs POST_CTS/POST_GRT hooks via source_step_tcl -> source INSIDE a proc, so plain top-level
# set made proc locals and cqb_seed failed on ::cqb_msafe (rp1clk lb/lbw cts.tcl:87).  Run the whole hook at global scope
# (same as face_flops.tcl / tap_balance.tcl) so the knobs are real globals for the procs.
uplevel #0 {
source /work/clock_family.tcl
proc cqb_env {name def} { expr {[info exists ::env($name)] && $::env($name) ne "" ? $::env($name) : $def} }
set cqb_off   [cqb_env CQB_OFF 10.0]
set cqb_win   [cqb_env CQB_WIN 20.0]
set cqb_cap   [cqb_env CQB_CAP 75.0]
set cqb_iters [cqb_env CQB_ITERS 3]
set cqb_split [cqb_env CQB_SPLIT 0]
set cqb_msafe [cqb_env CQB_MACRO_SAFE 0]
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
    # A clock net may drive both registers and deeper CTS buffers. Rehang
    # only its measured clock sinks, leaving all downstream CTS branches alone.
    # Row: inputs mean low high count pairs ({arrival iterm} sorted by arrival)
    set pairs [lsort -real -index 0 $vals]
    set inputs {}; set sum 0
    foreach row $pairs {lappend inputs [lindex $row 1]; set sum [expr {$sum+[lindex $row 0]}]}
    dict set out $nn [list $inputs [expr {$sum/[llength $pairs]}] [lindex $pairs 0 0] [lindex $pairs end 0] [llength $pairs] $pairs]
  }
  return $out
}
# seed point for a delay chain: the first sink's instance origin (codex default); CQB_MACRO_SAFE: for a macro
# sink, the point just outside the macro outline on the edge nearest the clock pin
proc cqb_seed {input} {
  set inst [$input getInst]; set bb [$inst getBBox]
  set x [$bb xMin]; set y [$bb yMin]
  if {!$::cqb_msafe || ![[$inst getMaster] isBlock]} { return [list $x $y] }
  set pb [$input getBBox]
  set px [expr {([$pb xMin]+[$pb xMax])/2}]; set py [expr {([$pb yMin]+[$pb yMax])/2}]
  set gap [expr {round(6.0*[[ord::get_db_tech] getDbUnitsPerMicron])}]
  set d [list [list [expr {$px-[$bb xMin]}] [expr {[$bb xMin]-$gap}] $py] \
              [list [expr {[$bb xMax]-$px}] [expr {[$bb xMax]+$gap}] $py] \
              [list [expr {$py-[$bb yMin]}] $px [expr {[$bb yMin]-$gap}]] \
              [list [expr {[$bb yMax]-$py}] $px [expr {[$bb yMax]+$gap}]]]
  set best [lindex [lsort -real -index 0 $d] 0]
  set core [[ord::get_db_block] getCoreArea]
  set sx [expr {min(max([lindex $best 1],[$core xMin]),[$core xMax]-$gap)}]
  set sy [expr {min(max([lindex $best 2],[$core yMin]),[$core yMax]-$gap)}]
  puts "CQB macro-safe seed [$inst getName] -> [expr {$sx/1000.0}] [expr {$sy/1000.0}]"
  return [list $sx $sy]
}
proc cqb_hang {inputs n tag} {
  set blk [ord::get_db_block]; set master [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
  if {$master eq "NULL"} {error "CQB missing delay cell"}
  set input [lindex $inputs 0]
  set original [$input getNet]
  lassign [cqb_seed $input] x y
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
puts "CQB knobs off $cqb_off win $cqb_win cap $cqb_cap iters $cqb_iters split $cqb_split macro_safe $cqb_msafe"
for {set cqb_iter 0} {$cqb_iter<$cqb_iters} {incr cqb_iter} {
  set cqb_m [cqb_measure]
  if {![dict size $cqb_m]} {error "CQB no direct clock-sink groups"}
  set target -1e9; set min 1e9; set max -1e9
  dict for {nn row} $cqb_m {
    set target [expr {max($target,[lindex $row 1])}]
    set min [expr {min($min,[lindex $row 2])}]
    set max [expr {max($max,[lindex $row 3])}]
  }
  puts "CQB iter$cqb_iter branches[dict size $cqb_m] sink_range $min $max mean_target $target"
  if {$cqb_iter==0} {set cqb_target [expr {$target-$cqb_off}]}
  set todo {}; set cqb_count 0
  dict for {nn row} $cqb_m {
    lassign $row input mean low high count pairs
    if {$cqb_split} {
      # only the sinks below the window; the rest of the group stays on its net
      set lo [expr {$cqb_target-$cqb_win/2.0}]
      set sub {}; set s 0
      foreach p $pairs { if {[lindex $p 0] < $lo} { lappend sub $p; set s [expr {$s+[lindex $p 0]}] } }
      if {![llength $sub]} continue
      set input [lmap p $sub {lindex $p 1}]
      set mean [expr {$s/[llength $sub]}]; set high [lindex $sub end 0]
      set delay [expr {min($cqb_cap,$cqb_target-$mean,$cqb_target+$cqb_win/2.0-$high)}]
    } else {
      set delay [expr {min($cqb_cap,$cqb_target-$mean,$cqb_target+$cqb_win-$high)}]
    }
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
}
