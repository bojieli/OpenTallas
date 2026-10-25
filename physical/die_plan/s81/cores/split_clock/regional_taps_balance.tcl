# S81-CORES/SPLIT POST_CTS: balance the regional taps (owner rule 10-23: taps within <= 20 ps), measure, then the kit's
# (skipped-CTS) repair at the default buffer budget.  Delay cells go in FRONT of a tap buffer (tap input side), never on
# a leaf.  Arrival basis = placement RC here; the routed-RCX bound is checked at sign-off (F1).
uplevel #0 {
set rb_blk [ord::get_db_block]
set rb_win [expr {[info exists ::env(OT_RT_WIN_PS)] ? $::env(OT_RT_WIN_PS) : 20.0}]
set rb_dm [[ord::get_db] findMaster BUFx4_ASAP7_75t_R]
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
proc rb_taps {} {
  global rb_blk
  set t {}
  set fh [open /work/ot_rt_taps.txt]; set names [split [string trim [read $fh]] "\n"]; close $fh
  foreach n $names { set i [$rb_blk findInst $n]
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
set rb_added 0
# CLOCK-RESET 10-25 (GEOM-REVIEW-3 06:59 vsw f6s: 22 ps BUFx4 quantum + target frozen at it0 -> h3_7 never padded,
# window 20.7): the target is RE-TAKEN every iteration = the max mean of the taps not yet padded (the naturally latest
# taps; all taps once every tap is padded).  Coarse unit = one pad stage (OT_RT_PAD_LADDER middle, BUFx4, ~20 ps) in
# front of the tap; fine unit = the drive of the LAST pad on the ladder BUFx6f..BUFx2 (a few ps per step, no extra
# stage; the tap buffer itself is never resized: its input cap changes the upstream delay the other way).  A tap that
# overshoots steps back (stronger last pad, else drops it).  A tap whose error changed sign is held at window/2.
# Converges to |mean - target| <= OT_RT_TOL_PS (window/4) or stops after OT_RT_BAL_IT (10) iterations.
set rb_tol [expr {[info exists ::env(OT_RT_TOL_PS)] ? $::env(OT_RT_TOL_PS) : $rb_win / 4.0}]
set rb_nit [expr {[info exists ::env(OT_RT_BAL_IT)] ? $::env(OT_RT_BAL_IT) : 10}]
set rb_ladder [expr {[info exists ::env(OT_RT_PAD_LADDER)] ? $::env(OT_RT_PAD_LADDER) : \
  "BUFx6f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx4_ASAP7_75t_R BUFx3_ASAP7_75t_R BUFx2_ASAP7_75t_R"}]
set rb_lad {}; foreach n $rb_ladder { set mm [[ord::get_db] findMaster $n]; if {$mm ne "NULL" && $mm ne ""} { lappend rb_lad $mm } }
set rb_mid [expr {[llength $rb_lad] / 2}]
set rb_pads {}
set rb_sign {}
set rb_unit 20.0
proc rb_tapin {ti} { foreach x [$ti getITerms] { if {[[$x getMTerm] getIoType] eq "INPUT" && [$x getNet] ne "NULL"} { return $x } }; return "" }
proc rb_np {t} { global rb_pads; return [expr {[dict exists $rb_pads $t] ? [llength [dict get $rb_pads $t]] : 0}] }
proc rb_add_pad {t it k} {
  global rb_blk rb_lad rb_pads rb_added
  set mm [lindex $rb_lad $k]
  set ti [$rb_blk findInst $t]; set inp [rb_tapin $ti]; set b [$ti getBBox]
  set j [rb_np $t]
  set di [odb::dbInst_create $rb_blk $mm "${t}_pad${it}_$j"]
  set nx [odb::dbNet_create $rb_blk "${t}_pad${it}_${j}_n"]; $nx setSigType CLOCK
  set src [$inp getNet]
  foreach x [$di getITerms] { set mt [$x getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { $x connect $src } elseif {[$mt getIoType] eq "OUTPUT"} { $x connect $nx } }
  $di setLocation [expr {[$b xMin] - ($j+1)*2*[[lindex $rb_lad 0] getWidth]}] [$b yMin]; $di setPlacementStatus PLACED
  $inp disconnect; $inp connect $nx
  dict lappend rb_pads $t [list $di $nx $k]; incr rb_added
}
proc rb_drop_pad {t} {
  # the last pad sits directly in front of the tap: reconnect the tap to the pad's input net, delete the pad
  global rb_blk rb_pads rb_added
  set l [dict get $rb_pads $t]; lassign [lindex $l end] di nx k
  set ti [$rb_blk findInst $t]; set inp [rb_tapin $ti]
  set src ""; foreach x [$di getITerms] { if {[[$x getMTerm] getIoType] eq "INPUT"} { set src [$x getNet] } }
  $inp disconnect; $inp connect $src
  odb::dbInst_destroy $di; odb::dbNet_destroy $nx
  dict set rb_pads $t [lrange $l 0 end-1]; incr rb_added -1
}
proc rb_resize_last {t dir} {
  # dir +1 = slower (weaker last pad), -1 = faster; returns 1 when changed
  global rb_pads rb_lad
  if {![rb_np $t]} { return 0 }
  set l [dict get $rb_pads $t]; lassign [lindex $l end] di nx k
  set k2 [expr {$k + $dir}]
  if {$k2 < 0 || $k2 >= [llength $rb_lad]} { return 0 }
  $di swapMaster [lindex $rb_lad $k2]
  dict set rb_pads $t [lreplace $l end end [list $di $nx $k2]]
  return 1
}
for {set it 0} {$it < $rb_nit} {incr it} {
  set m [rb_measure]
  set hi -1.0; dict for {t v} $m { if {![rb_np $t]} { set hi [expr {max($hi,[lindex $v 0])}] } }
  if {$hi < 0} { dict for {t v} $m { set hi [expr {max($hi,[lindex $v 0])}] } }
  set lo 1e9; set mx 0.0; dict for {t v} $m { set lo [expr {min($lo,[lindex $v 0])}]; set mx [expr {max($mx,[lindex $v 0])}] }
  set line "OT_RT_BAL it$it target [format %.1f $hi] window [format %.1f [expr {$mx-$lo}]]:"
  dict for {t v} $m { append line " $t=[format %.0f [lindex $v 0]]([format %.0f [lindex $v 1]]-[format %.0f [lindex $v 2]],[lindex $v 3])/[rb_np $t]" }
  puts $line
  set todo 0
  dict for {t v} $m {
    set d [expr {$hi - [lindex $v 0]}]
    set sg [expr {$d > 0 ? 1 : -1}]
    set tl $rb_tol
    if {[dict exists $rb_sign $t] && [dict get $rb_sign $t] != $sg} { set tl [expr {$rb_win / 2.0}] }
    if {abs($d) <= $tl} continue
    dict set rb_sign $t $sg
    if {$d > 0} {
      if {$d > $rb_unit - $rb_tol} {
        # coarse: floor pad stages at the middle drive (never overshoot by a whole stage); residual trimmed next pass
        set nb [expr {max(1, int(floor(($d + $rb_tol) / $rb_unit)))}]
        for {set j 0} {$j < $nb} {incr j} { rb_add_pad $t $it $rb_mid }
      } elseif {![rb_resize_last $t 1]} {
        rb_add_pad $t $it 0
      }
      set todo 1
    } elseif {[rb_np $t]} {
      if {![rb_resize_last $t -1]} { rb_drop_pad $t }
      set todo 1
    }
  }
  if {!$todo} break
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
      if {$d <= 8.0} continue
      set todo 1
      set nb [expr {max(1, int(round($d / 18.0 * 0.75)))}]
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
puts "OT_RT_BAL done: $rb_added pad cells; tap means [format %.0f $lo]..[format %.0f $hi] ps (window [format %.0f [expr {$hi-$lo}]] vs $rb_win)"
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
