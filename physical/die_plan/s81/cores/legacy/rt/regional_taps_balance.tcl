# COPY for gen_core_kit_legacy.py regional_taps (KITS-SPARE/S81C 10-25) of physical/die_plan/s81/cores/split_clock/regional_taps_balance.tcl
# @ codex/s81-physical-0719 6e336af2ba (S81-CORES/SPLIT + Codex planned-spine protection / guard); + OT_RT_SETUP_ONLY.
# S81-CORES/SPLIT POST_CTS: balance the regional taps (owner rule 10-23: taps within <= 20 ps), measure, then the kit's
# (skipped-CTS) repair at the default buffer budget.  Delay cells go in FRONT of a tap buffer (tap input side), never on
# a leaf.  Arrival basis = placement RC here; the routed-RCX bound is checked at sign-off (F1).
uplevel #0 {
if {[file exists /work/clock_spine_guard.tcl]} { source /work/clock_spine_guard.tcl }
set rb_blk [ord::get_db_block]
set rb_win [expr {[info exists ::env(OT_RT_WIN_PS)] ? $::env(OT_RT_WIN_PS) : 20.0}]
set rb_dm [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]
# S81-CORES-KITS-8 2026-10-31 pad model fix (clock tool, not a pad tweak): measured BUFx2 pad stage = 18.6 (vn_a) /
# 18.7 (vn_b) ps placement RC TT, the old 9.0 ps model doubled every chain (vn_a/vn_b macro -81 -> +48/+50 ps late, routed
# pair skew 85-91 > 80).  Stage delay from OT_RT_PAD_PS (default 18.5); an overshoot (macro > regs + 8 ps) removes the
# pin's own ot_rt_mpad cells again (the old loop only ever added).
set rb_pad_ps [expr {[info exists ::env(OT_RT_PAD_PS)] ? $::env(OT_RT_PAD_PS) : 18.5}]
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
for {set it 0} {$it < 4} {incr it} {
  set m [rb_measure]
  set hi 0.0; dict for {t v} $m { set hi [expr {max($hi,[lindex $v 0])}] }
  set line "OT_RT_BAL it$it:"; dict for {t v} $m { append line " $t=[format %.0f [lindex $v 0]]([format %.0f [lindex $v 1]]-[format %.0f [lindex $v 2]],[lindex $v 3])" }
  puts $line
  set todo 0
  dict for {t v} $m {
    set d [expr {$hi - [lindex $v 0]}]
    if {$d <= $rb_win / 2.0} continue
    set todo 1
    set nb [expr {max(1, int(round($d / $rb_pad_ps * 0.75)))}]
    set ti [$rb_blk findInst $t]
    set inp ""; foreach x [$ti getITerms] { if {[[$x getMTerm] getIoType] eq "INPUT" && [$x getNet] ne "NULL"} { set inp $x; if {[[$x getMTerm] getName] eq "CLK"} break } }
    set src [$inp getNet]; set b [$ti getBBox]
    # The pre-balance guard already proved CTS kept this exact arm. Unlock just
    # this tap's intentional pad splice, then protect it again below.
    if {[info exists ::env(OT_RT_PROTECT_SPINE)] && $::env(OT_RT_PROTECT_SPINE)} {
      unset_dont_touch [get_nets -quiet [$src getName]]
      unset_dont_touch [get_cells -quiet [$ti getName]]
    }
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
    if {[info exists ::env(OT_RT_PROTECT_SPINE)] && $::env(OT_RT_PROTECT_SPINE)} {
      set_dont_touch [get_nets -quiet [$src getName]]
      # an ICG clone tap (ot_rtg_*) also has a DATA input (ENA): keep the cell free so hold/DRV repair can buffer the
      # enable net (dont_touch on the cell blocked RSZ insert_buffer on u_e.cg_en_g: RSZ-3006, ROM qxpq rti GRT 10-31)
      if {![string match ot_rtg_* $t]} { set_dont_touch [get_cells -quiet [$ti getName]] }
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
    if {![string match ot_rt_mtap* $tap] && ![string match ot_rtg_mtap* $tap]} continue
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
      if {$d < -8.0} {
        set nr [expr {max(1, int(round(-$d / $rb_pad_ps)))}]; set rm 0
        while {$rm < $nr} {
          set pn [$it getNet]; set drv ""; set loads 0
          foreach y [$pn getITerms] { if {[[$y getMTerm] getIoType] eq "OUTPUT"} { set drv [$y getInst] } elseif {[[$y getMTerm] getIoType] eq "INPUT"} { incr loads } }
          if {$drv eq "" || $loads != 1 || ![string match ot_rt_mpad* [$drv getName]]} break
          set inn ""; foreach y [$drv getITerms] { set mt [$y getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue; if {[$mt getIoType] eq "INPUT"} { set inn [$y getNet] } }
          if {$inn eq "" || $inn eq "NULL"} break
          $it disconnect; odb::dbInst_destroy $drv; odb::dbNet_destroy $pn; $it connect $inn; incr rm
        }
        puts "OT_RT_MACRO_REMOVE pass$mi [[$it getInst] getName] overshoot [format %+.0f [expr {-$d}]] ps: removed $rm of $nr pad cells"
        if {$rm} { set todo 1 }
        continue
      }
      if {$d <= 8.0} continue
      set todo 1
      set nb [expr {max(1, int(round($d / $rb_pad_ps * 0.75)))}]
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
  # KITS-SPARE 10-25 modern core flow: setup-only here, hold only in the FF frame (FF-only GRT hold step)
  if {[info exists ::env(OT_RT_SETUP_ONLY)] && $::env(OT_RT_SETUP_ONLY)} { repair_timing_helper -setup } else { repair_timing_helper }
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
