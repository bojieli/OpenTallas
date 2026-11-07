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
      set lf [rb_em_lf_plan [[$it getInst] getName]]
      if {[dict size $lf]} {
        rb_em_lf_connect $it $lf $tgt
        incr rb_em_lf_count
        dict set rb_em_targets [[$it getInst] getName] [list $it $g $tgt $tap localface 0 0]
        continue
      }
      # an ETM child (OT_RT_ETM_MASTER_RE) is landed below by its own rule, not pin-matched to its regs
      if {[info exists ::env(OT_RT_ETM_MASTER_RE)] && $::env(OT_RT_ETM_MASTER_RE) ne "" && [regexp $::env(OT_RT_ETM_MASTER_RE) [[[$it getInst] getMaster] getName]]} continue
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
# ETM macro clock landing (DIE-S81-75 11-07, opt-in OT_RT_ETM_MASTER_RE + OT_RT_ETM_EARLY_PS). A hardened child with an internal
# clock tree has its latency in the ETM lib: min/max_clock_tree_path and hold ~= +latency, setup ~= -latency on every input. F3
# above matches the clk PIN to the interface regs, which lands the child's real flops one internal latency AFTER those regs: every
# short input path then fails hold by about that latency (bksel hist_bank: 2900 endpoints, -108 FF, CQ+INV 43 vs lib hold 123).
# Land the pin OT_RT_ETM_EARLY_PS (TT, placement RC) before its interface regs instead: tap the chain AHEAD of the macro tap at the
# node whose arrival fits, isolated by one buffer so the node keeps its load. Regs stay where the balance loop put them, so
# insertion does not grow. Delay stays on the regs branch, the common path up to the node keeps its CPPR credit.
if {[info exists ::env(OT_RT_ETM_MASTER_RE)] && $::env(OT_RT_ETM_MASTER_RE) ne ""} {
  set rb_em_x [expr {double($::env(OT_RT_ETM_EARLY_PS))}]
  set rb_em_isom [[ord::get_db] findMaster [expr {[info exists ::env(OT_RT_ETM_ISO)] ? $::env(OT_RT_ETM_ISO) : "BUFx8_ASAP7_75t_R"}]]
  set rb_em_isops [expr {[info exists ::env(OT_RT_ETM_ISO_PS)] ? double($::env(OT_RT_ETM_ISO_PS)) : 25.0}]
  proc rb_em_arr {name mterm} {
    set p [get_pins -quiet "$name/$mterm"]
    if {$p eq "" || [catch {set a [get_property $p arrival_max_rise]}] || $a eq ""} { return "" }
    return $a
  }
  proc rb_em_io {inst dir} {
    foreach y [$inst getITerms] { set mt [$y getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
      if {[$mt getIoType] eq $dir && [$y getNet] ne "NULL"} { return $y } }
    return ""
  }
  proc rb_em_driver {net} {
    foreach y [$net getITerms] { if {[[$y getMTerm] getIoType] eq "OUTPUT"} { return $y } }
    return ""
  }
# BKSEL RF8 localface candidate, default OFF.  The two formerly far BUF8 leaves
# are placed by the actual bottom CLK faces. Three corridor BUF24 stages per
# branch keep placement-RC wire/load within the reviewed branch-drive budget.
# This is a physical topology, not a delay-padding loop: it never changes the
# 160ps target or interface-register trees, and rejects an out-of-band landing.
proc rb_em_lf_plan {nm} {
  if {![info exists ::env(OT_RT_ETM_LOCALFACE)] || !$::env(OT_RT_ETM_LOCALFACE)} { return {} }
  set plain [string map [list \\ ""] $nm]
  switch -exact -- $plain {
    {u_q.u_s.u_hc.g_bank[0].u_bank} {
      return [dict create source ot_rt_h3_0 xy {{105.624 125.010} {105.624 61.290} {79.974 19.980}} leaf {36.180 19.980} extra_ps 179.0]
    }
    {u_q.u_s.u_hc.g_bank[2].u_bank} {
      return [dict create source ot_rt_h3_0 xy {{185.004 160.110} {185.004 89.910} {185.328 55.080}} leaf {235.764 20.520} extra_ps 184.0]
    }
  }
  return {}
}
proc rb_em_lf_io {i dir} {
  foreach t [$i getITerms] {
    set m [$t getMTerm]
    if {[$m getSigType] ni {POWER GROUND} && [$m getIoType] eq $dir} { return $t }
  }
  error "OT_RT_ETM_LOCALFACE missing $dir pin on [$i getName]"
}
proc rb_em_lf_place {i xy} {
  global rb_blk
  set u [[ord::get_db_tech] getDbUnitsPerMicron]
  lassign $xy x y; set x [expr {int(round($x*$u))}]; set y [expr {int(round($y*$u))}]
  set row ""
  foreach r [$rb_blk getRows] {
    set bb [$r getBBox]
    if {[$bb yMin] == $y && [$bb xMin] <= $x && $x+[[$i getMaster] getWidth] <= [$bb xMax]} { set row $r; break }
  }
  if {$row eq ""} { error "OT_RT_ETM_LOCALFACE no legal row at $xy" }
  $i setOrient [$row getOrient]
  $i setLocation $x $y
  $i setPlacementStatus FIRM
}
proc rb_em_lf_connect {it plan tgt} {
  global rb_blk rb_em_n
  set src [$rb_blk findInst [dict get $plan source]]
  if {$src eq "NULL" || $src eq "" || [[$src getMaster] getName] ne "BUFx24_ASAP7_75t_R"} {
    error "OT_RT_ETM_LOCALFACE source missing or not reviewed BUF24"
  }
  set sp [rb_em_lf_io $src OUTPUT]; set prev [$sp getNet]
  set a [rb_em_arr [$src getName] [[$sp getMTerm] getName]]
  if {$a eq ""} {error "OT_RT_ETM_LOCALFACE source arrival unavailable"}
  # Reviewed NLDM + calibrated wire-RC estimate includes source added load,
  # all corridor stages, local BUF8, macro2.9406fF CLK load, and <=7um leaf wire.
  # A source whose projected landing is late is rejected before modifying nets.
  if {$a+[dict get $plan extra_ps] > $tgt+15.0} {
    error "OT_RT_ETM_LOCALFACE source/driver budget too late: $a + [dict get $plan extra_ps] vs $tgt"
  }
  set old [$it getNet]; set seq 0
  set shapes [concat [dict get $plan xy] [list [dict get $plan leaf]]]
  foreach xy $shapes {
    incr seq; set master [expr {$seq == 4 ? "BUFx8_ASAP7_75t_R" : "BUFx24_ASAP7_75t_R"}]
    set dm [[ord::get_db] findMaster $master]
    if {$dm eq "NULL" || $dm eq ""} {error "OT_RT_ETM_LOCALFACE missing $master"}
    set nm "ot_rt_etm_lf[incr rb_em_n]"
    set di [odb::dbInst_create $rb_blk $dm $nm]
    set nx [odb::dbNet_create $rb_blk "${nm}_n"]; $nx setSigType CLOCK
    [rb_em_lf_io $di INPUT] connect $prev; [rb_em_lf_io $di OUTPUT] connect $nx
    rb_em_lf_place $di $xy
    set_dont_touch [get_cells -quiet $nm]
    set prev $nx
  }
  $it disconnect; $it connect $prev
  # The old macro branch is now empty. Keep the upstream register tree intact.
  set cur $old
  while {1} {
    set loads 0
    foreach t [$cur getITerms] {if {[[$t getMTerm] getIoType] eq "INPUT"} {incr loads}}
    if {$loads} break
    set d [rb_em_driver $cur]; if {$d eq ""} break
    set di [$d getInst]; set ip [rb_em_io $di INPUT]
    if {$ip eq "" || [string match ot_rt_mtap* [$di getName]]} break
    set up [$ip getNet]; odb::dbInst_destroy $di; odb::dbNet_destroy $cur; set cur $up
  }
  puts "OT_RT_ETM_LOCALFACE [[$it getInst] getName] source [$src getName] rise $a budget [dict get $plan extra_ps] target $tgt; 3 corridor BUF24 + macroface BUF8, no padding feedback"
}

  set_propagated_clock [all_clocks]; estimate_parasitics -placement
  set rb_em_targets {}; set rb_em_n 0; set rb_em_lf_count 0
  if {[info exists ::env(OT_RT_ETM_LOCALFACE)] && $::env(OT_RT_ETM_LOCALFACE) && $rb_em_x != 160.0} {
    error "OT_RT_ETM_LOCALFACE requires unchanged 160ps ETM target"
  }
  dict for {tap net} [rb_taps] {
    if {![string match ot_rt_mtap* $tap]} continue
    set s 0.0; set k 0; set mp {}
    foreach it [rb_sinks $net] {
      set p [get_pins -quiet "[[$it getInst] getName]/[[$it getMTerm] getName]"]
      if {$p eq "" || [catch {set a [get_property $p arrival_max_rise]}] || $a eq ""} continue
      if {[[[$it getInst] getMaster] getType] eq "BLOCK"} {
        if {[regexp $::env(OT_RT_ETM_MASTER_RE) [[[$it getInst] getMaster] getName]]} { lappend mp [list $it $a] }
      } else { set s [expr {$s+$a}]; incr k }
    }
    if {!$k || ![llength $mp]} continue
    set g [expr {$s/$k}]; set tgt [expr {$g - $rb_em_x}]
    foreach x $mp { lassign $x it a
      # walk up from the macro tap input to the first node early enough for node + isolation buffer
      set n [[rb_em_io [$rb_blk findInst $tap] INPUT] getNet]
      set drvi ""; set hops 0
      while {1} {
        set d [rb_em_driver $n]
        if {$d eq ""} { set na 0.0; break }
        set drvi [$d getInst]
        set na [rb_em_arr [$drvi getName] [[$d getMTerm] getName]]
        if {$na eq ""} { error "OT_RT_ETM no arrival at [$drvi getName]" }
        if {$na + $rb_em_isops <= $tgt} break
        set i [rb_em_io $drvi INPUT]
        if {$i eq ""} { error "OT_RT_ETM no input on [$drvi getName]" }
        set n [$i getNet]; incr hops
      }
      set old [$it getNet]; set bb [$it getBBox]
      set isoi [odb::dbInst_create $rb_blk $rb_em_isom "ot_rt_etm_iso[incr rb_em_n]"]
      set ison [odb::dbNet_create $rb_blk "ot_rt_etm_iso${rb_em_n}_n"]; $ison setSigType CLOCK
      set nn [$n getName]
      if {[info exists ::env(OT_RT_PROTECT_SPINE)] && $::env(OT_RT_PROTECT_SPINE)} { unset_dont_touch [get_nets -quiet $nn] }
      foreach y [$isoi getITerms] { set mt [$y getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
        if {[$mt getIoType] eq "INPUT"} { $y connect $n } elseif {[$mt getIoType] eq "OUTPUT"} { $y connect $ison } }
      if {[info exists ::env(OT_RT_PROTECT_SPINE)] && $::env(OT_RT_PROTECT_SPINE)} { set_dont_touch [get_nets -quiet $nn] }
      if {$drvi ne ""} { set db [$drvi getBBox]; $isoi setLocation [$db xMin] [expr {[$db yMin] + 2*[$rb_dm getHeight]}] } else { $isoi setLocation [$bb xMin] [$bb yMin] }
      $isoi setPlacementStatus PLACED
      $it disconnect; $it connect $ison
      # the macro's old branch has no load now: remove it up to the tap net, which keeps the regs tree
      set cur $old; set rm 0
      while {1} {
        set loads 0; foreach y [$cur getITerms] { if {[[$y getMTerm] getIoType] eq "INPUT"} { incr loads } }
        if {$loads} break
        set d [rb_em_driver $cur]; if {$d eq ""} break
        set di [$d getInst]; if {[$di getName] eq $tap} break
        set i [rb_em_io $di INPUT]; if {$i eq ""} break
        set up [$i getNet]; odb::dbInst_destroy $di; odb::dbNet_destroy $cur; set cur $up; incr rm
      }
      dict set rb_em_targets [[$it getInst] getName] [list $it $g $tgt $tap $nn $hops $rm]
    }
  }
  detailed_placement
  if {[info exists ::env(OT_RT_ETM_LOCALFACE)] && $::env(OT_RT_ETM_LOCALFACE) && $rb_em_lf_count != 2} {
    error "OT_RT_ETM_LOCALFACE expected exactly two reviewed macro landings, got $rb_em_lf_count"
  }
  # second pass: an over-early pin (node granularity, wire) gets BUFx2 pads, one estimate at a time; never above target
  for {set pp 0} {$pp < 2} {incr pp} {
    set_propagated_clock [all_clocks]; estimate_parasitics -placement
    set todo 0
    dict for {nm v} $rb_em_targets { lassign $v it g tgt tap nn hops rm
      set a [rb_em_arr $nm [[$it getMTerm] getName]]
      puts "OT_RT_ETM pass$pp $nm clk [format %.0f $a] regs mean [format %.0f $g] target [format %.0f $tgt] ($tap, node $nn, $hops hops up, $rm old cells removed)"
      if {[dict size [rb_em_lf_plan $nm]]} {
        set ld [rb_em_driver [$it getNet]]
        if {$ld eq "" || [[[$ld getInst] getMaster] getName] ne "BUFx8_ASAP7_75t_R"} {
          error "OT_RT_ETM_LOCALFACE leaf missing or resized"
        }
        set lb [$ld getBBox]; set mb [$it getBBox]
        set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
        set leaf_reach [expr {(abs(([$lb xMin]+[$lb xMax])-([$mb xMin]+[$mb xMax]))+abs(([$lb yMin]+[$lb yMax])-([$mb yMin]+[$mb yMax])))/2.0/$dbu}]
        if {$leaf_reach > 8.0} {error "OT_RT_ETM_LOCALFACE macroface output moved: $nm reach $leaf_reach um"}
        if {abs($a-$tgt)>15.0} {error "OT_RT_ETM_LOCALFACE actual landing out of target band: $nm $a vs $tgt"}
        continue
      }
      if {$a >= $tgt - 15.0} continue
      set nb [expr {int(floor(($tgt - $a) / $rb_pad_ps))}]
      if {$nb < 1} continue
      set todo 1; set prev [$it getNet]; set bb [$it getBBox]
      for {set j 0} {$j < $nb} {incr j} {
        set di [odb::dbInst_create $rb_blk $rb_dm "ot_rt_etm_pad[incr rb_em_n]"]
        set nx [odb::dbNet_create $rb_blk "ot_rt_etm_pad${rb_em_n}_n"]; $nx setSigType CLOCK
        foreach y [$di getITerms] { set mt [$y getMTerm]; if {[$mt getSigType] in {POWER GROUND}} continue
          if {[$mt getIoType] eq "INPUT"} { $y connect $prev } elseif {[$mt getIoType] eq "OUTPUT"} { $y connect $nx } }
        $di setLocation [expr {[$bb xMin] - 3*[[ord::get_db_tech] getDbUnitsPerMicron] - $j*2*[$rb_dm getWidth]}] [expr {[$bb yMin] - 2*[$rb_dm getHeight]}]; $di setPlacementStatus PLACED
        set prev $nx
      }
      $it disconnect; $it connect $prev
    }
    if {!$todo} break
    detailed_placement
  }
  set_propagated_clock [all_clocks]; estimate_parasitics -placement
  set wmn 1e9; set wmx -1e9
  dict for {nm v} $rb_em_targets { lassign $v it g tgt
    set a [rb_em_arr $nm [[$it getMTerm] getName]]
    set wmn [expr {min($wmn,$g-$a)}]; set wmx [expr {max($wmx,$g-$a)}] }
  puts "OT_RT_ETM done: [dict size $rb_em_targets] macros landed early by [format %.0f $wmn]..[format %.0f $wmx] ps vs their regs (target $rb_em_x, TT placement RC)"
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
