# S81-CORES/SPLIT POST_CTS: balance the regional taps (owner rule 10-23: taps within <= 20 ps), measure, then the kit's
# (skipped-CTS) repair at the default buffer budget.  Delay cells go in FRONT of a tap buffer (tap input side), never on
# a leaf.  Arrival basis = placement RC here; the routed-RCX bound is checked at sign-off (F1).
uplevel #0 {
set rb_blk [ord::get_db_block]
set rb_win [expr {[info exists ::env(OT_RT_WIN_PS)] ? $::env(OT_RT_WIN_PS) : 20.0}]
# pad unit: the smallest buffer (GEOM-REVIEW-3 06:59 vsw f6s: BUFx4 padded in ~22 ps quanta, window ended 20.7 vs 20).
# The per-cell delay is MEASURED after every pass (mean shift / cells added) and the target is re-taken every pass.
set rb_dm [[ord::get_db] findMaster [expr {[info exists ::env(OT_RT_PAD_CELL)] ? $::env(OT_RT_PAD_CELL) : "BUFx2_ASAP7_75t_R"}]]
if {$rb_dm eq "NULL"} { error "OT_RT_BAL: pad cell not found" }
set rb_step [expr {[info exists ::env(OT_RT_PAD_PS)] ? $::env(OT_RT_PAD_PS) : 10.0}]
set rb_tol [expr {[info exists ::env(OT_RT_TOL_PS)] ? $::env(OT_RT_TOL_PS) : $rb_win / 4.0}]
proc rb_sinks {net} {
  set out {}; set todo [list $net]; set seen {}
  while {[llength $todo]} {
    set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
    if {[dict exists $seen [$n getName]]} continue; dict set seen [$n getName] 1
    foreach it [$n getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set i [$it getInst]; set m [[$i getMaster] getName]
      if {[string match BUF* $m] || [string match INV* $m] || [string match CKINV* $m]} {
        foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT" && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
      } else { lappend out $it }
    }
  }
  return $out
}
# pure planner (testable without OpenDB/STA): means = tap -> mean arrival; target = the CURRENT latest mean; a tap gets
# round(d / step) cells when its gap d exceeds max(tol, step/2) (one more cell would overshoot by more than it closes).
proc rb_plan {means step tol} {
  set hi -1e18; dict for {t v} $means { set hi [expr {max($hi,$v)}] }
  set out {}
  dict for {t v} $means {
    set d [expr {$hi - $v}]
    if {$d <= max($tol, $step / 2.0)} continue
    dict set out $t [expr {max(1, int(round($d / $step)))}]
  }
  return $out
}
# measured pad delay per cell from the last pass (taps that got cells: mean shift / cells); keeps the old step when
# nothing usable was measured.  shift is relative to the untouched taps' mean shift (re-placement moves everyone).
proc rb_learn {before after added step} {
  set s0 0.0; set k0 0
  dict for {t v} $after { if {![dict exists $added $t] && [dict exists $before $t]} { set s0 [expr {$s0 + $v - [dict get $before $t]}]; incr k0 } }
  set base [expr {$k0 ? $s0 / $k0 : 0.0}]
  set s 0.0; set n 0
  dict for {t c} $added { if {[dict exists $after $t] && [dict exists $before $t]} {
      set s [expr {$s + [dict get $after $t] - [dict get $before $t] - $base}]; incr n $c } }
  if {$n == 0 || $s <= 0} { return $step }
  return [expr {max(2.0, $s / $n)}]
}
proc rb_taps {} {
  global rb_blk
  set t {}
  set fh [open /work/ot_rt_taps.txt]; set names [split [string trim [read $fh]] "\n"]; close $fh
  foreach n $names { set i [$rb_blk findInst $n]; if {$i eq "NULL"} continue
    foreach x [$i getITerms] { if {[[$x getMTerm] getIoType] eq "OUTPUT"} { dict set t $n [$x getNet] } } }
  return $t
}
proc rb_measure {} {
  set_propagated_clock [all_clocks]
  estimate_parasitics -placement
  set r {}
  dict for {tap net} [rb_taps] {
    set s 0.0; set k 0; set mn 1e9; set mx 0
    foreach it [rb_sinks $net] {
      set p [get_pins -quiet "[[$it getInst] getName]/[[$it getMTerm] getName]"]
      if {$p eq ""} continue
      if {[catch {set a [get_property $p arrival_max_rise]}] || $a eq ""} continue
      set s [expr {$s+$a}]; incr k; set mn [expr {min($mn,$a)}]; set mx [expr {max($mx,$a)}]
    }
    if {$k} { dict set r $tap [list [expr {$s/$k}] $mn $mx $k] }
  }
  return $r
}
set rb_added 0; set rb_prev {}; set rb_last {}
for {set it 0} {$it < 8} {incr it} {
  set m [rb_measure]
  set means {}; dict for {t v} $m { dict set means $t [lindex $v 0] }
  if {[dict size $rb_last]} { set rb_step [rb_learn $rb_prev $means $rb_last $rb_step] }
  set line "OT_RT_BAL it$it (step [format %.1f $rb_step] ps):"; dict for {t v} $m { append line " $t=[format %.1f [lindex $v 0]]([format %.0f [lindex $v 1]]-[format %.0f [lindex $v 2]],[lindex $v 3])" }
  puts $line
  set plan [rb_plan $means $rb_step $rb_tol]
  if {![dict size $plan]} break
  dict for {t nb} $plan {
    set ti [$rb_blk findInst $t]
    set inp ""; foreach x [$ti getITerms] { if {[[$x getMTerm] getIoType] eq "INPUT" && [$x getNet] ne "NULL"} { set inp $x } }
    set src [$inp getNet]; set b [$ti getBBox]
    set prev $src
    for {set j 0} {$j < $nb} {incr j} {
      set di [odb::dbInst_create $rb_blk $rb_dm "${t}_pad${it}_$j"]
      set nx [odb::dbNet_create $rb_blk "${t}_pad${it}_${j}_n"]; $nx setSigType CLOCK
      foreach x [$di getITerms] { set mt [$x getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
        if {[$mt getIoType] eq "INPUT"} { $x connect $prev } elseif {[$mt getIoType] eq "OUTPUT"} { $x connect $nx } }
      $di setLocation [expr {[$b xMin] - ($j+1)*2*[$rb_dm getWidth]}] [$b yMin]; $di setPlacementStatus PLACED
      set prev $nx; incr rb_added
    }
    $inp disconnect; $inp connect $prev
  }
  set rb_prev $means; set rb_last $plan
  detailed_placement
}

# F3 macro-interface skew group: each SRAM clock pin latency-matched to ITS interface registers (no internal clock latency
# in the SRAM lib): delay cells in front of the macro clk pin, at the pin, up to 3 passes at 3/4 of the estimate.
for {set mi 0} {$mi < 3} {incr mi} {
  set_propagated_clock [all_clocks]; estimate_parasitics -placement
  set todo 0
  dict for {tap net} [rb_taps] {
    if {![string match ot_rt_mtap* $tap]} continue
    set s 0.0; set k 0; set mp {}
    foreach it [rb_sinks $net] {
      set p [get_pins -quiet "[[$it getInst] getName]/[[$it getMTerm] getName]"]
      if {$p eq "" || [catch {set a [get_property $p arrival_max_rise]}] || $a eq ""} continue
      if {[[[$it getInst] getMaster] getType] eq "BLOCK"} { lappend mp [list $it $a] } else { set s [expr {$s+$a}]; incr k }
    }
    if {!$k} continue
    set g [expr {$s/$k}]
    foreach x $mp { lassign $x it a
      set d [expr {$g - $a}]
      puts "OT_RT_MACRO pass$mi [[$it getInst] getName] clk [format %.0f $a] vs interface regs mean [format %.0f $g] ($k regs): [format %+.0f [expr {-$d}]] ps"
      if {$d <= max(8.0, $::rb_step / 2.0)} continue
      set todo 1
      set nb [expr {max(1, int(round($d / $::rb_step)))}]
      set src [$it getNet]; set bb [$it getBBox]
      set prev $src
      for {set j 0} {$j < $nb} {incr j} {
        set di [odb::dbInst_create $rb_blk $rb_dm "ot_rt_mpad${mi}_[incr ::rb_added]"]
        set nx [odb::dbNet_create $rb_blk "ot_rt_mpad${mi}_${::rb_added}_n"]; $nx setSigType CLOCK
        foreach y [$di getITerms] { set mt [$y getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
          if {[$mt getIoType] eq "INPUT"} { $y connect $prev } elseif {[$mt getIoType] eq "OUTPUT"} { $y connect $nx } }
        $di setLocation [expr {[$bb xMin] - 3*[[ord::get_db_tech] getDbUnitsPerMicron] - $j*2*[$rb_dm getWidth]}] [$bb yMin]; $di setPlacementStatus PLACED
        set prev $nx
      }
      $it disconnect; $it connect $prev
    }
  }
  if {!$todo} break
  detailed_placement
}
set m [rb_measure]
set lo 1e9; set hi 0; dict for {t v} $m { set lo [expr {min($lo,[lindex $v 0])}]; set hi [expr {max($hi,[lindex $v 0])}] }
puts "OT_RT_BAL done: $rb_added pad cells; tap means [format %.1f $lo]..[format %.1f $hi] ps (window [format %.1f [expr {$hi-$lo}]] vs $rb_win, pad step [format %.1f $rb_step] ps): [expr {$hi-$lo <= $rb_win ? "PASS" : "FAIL"}]"
# pin-flop / all insertion and the FF-hold estimate before any repair (render + GEOM input)
set arr {}; foreach p [all_registers -clock_pins] { if {![catch {set a [get_property $p arrival_max_rise]}] && $a ne ""} { lappend arr $a } }
set arr [lsort -real $arr]
puts "OT_RT_INS all registers [llength $arr]: min [format %.1f [lindex $arr 0]] p50 [format %.1f [lindex $arr [expr {[llength $arr]/2}]]] max [format %.1f [lindex $arr end]] (placement RC, TT)"
puts "OT_RT_HOLD_PRE_REPAIR worst [format %.2f [expr {[sta::worst_slack_cmd min]*1e12}]] ps; viol [sta::endpoint_violation_count min]"
if {![info exists ::env(OT_RT_NO_REPAIR)] || !$::env(OT_RT_NO_REPAIR)} {
  repair_timing_helper
  detailed_placement
  check_placement -verbose
}
estimate_parasitics -placement
# per-register CK arrival dump (flow placement RC, TT) for the post-CTS render
set fh [open /work/ot_rt_ck_cts_tt.tsv w]
set rb_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set_propagated_clock [all_clocks]
foreach p [all_registers -clock_pins] {
  if {[catch {set a [get_property $p arrival_max_rise]}] || $a eq ""} continue
  set i [sta::sta_to_db_inst [$p instance]]; if {$i eq "NULL" || $i eq ""} continue
  set b [$i getBBox]
  puts $fh "[get_full_name $p]\t[format %.2f [expr {([$b xMin]+[$b xMax])/2.0/$rb_dbu}]]\t[format %.2f [expr {([$b yMin]+[$b yMax])/2.0/$rb_dbu}]]\t[format %.2f $a]\t[[$i getMaster] getName]"
}
close $fh

}
