# mscts_core.tcl -- STRUCTURED CLOCK for a single-clock hard core (QC-CQB2 2026-10-25, opt-in via OT_MSCTS_SPEC).
#
# Industry multi-source CTS at core scale (METHODOLOGY 3.2-3.5, owner 10-23 clock rule, GEOM verdict qfd_dv_s8x_vmr_cqb
# 2026-10-25 04:19 F5): a planned, equal-length repeated TRUNK from the clock port to a few REGIONAL TAPS; TritonCTS
# builds only the short local tree under each tap; every hard-macro clock pin gets its OWN short leaf (delay chain +
# leaf driver at the pin) hung on the trunk end of its nearest tap, latency-matched to the macro's interface registers.
# Taps are balanced to a common latency within OT_MSCTS_WIN_PS (default 20) on GRT RC (ot_ms_balance grt, POST_GLOBAL_
# ROUTE), never on placement RC (the CTS-stage pass is a coarse pre-balance only).
#
# Why (qfd_dv_s8x_vmr_cqb, routed review claude/qc-cqb-1025@8940062a7): one TritonCTS tree from the S-face port gave
# long diagonal leaf runs across the south strip, the SRAM clock pins on a 7-delay-buffer west branch 175 um from their
# east-edge write-data registers (+18-20 ps capture-late, 63 of 107 FF hold violators) and a GRT-estimate vs RCX
# clock-arrival error of +11.6..+45.2 ps that differed per branch, so the skew moved after route.  Equal trunk lengths
# (same stage count and same cells on every tap path, short repeated hops) keep the estimate error near common-mode, and the
# local trees are short.
#
# Construction (ot_ms_build, PRE_CTS after placement): root buffer at the spec root site, input = the clock port net.
# Every tap path = the spec polyline (Manhattan legs routed around the macros), cut into the SAME number N of equal
# stages (N = ceil(L_max / OT_MSCTS_SEG_UM)): every path has the identical cell chain (root, N trunk repeaters, tap
# buffer), so the cell delay is common-mode at every corner; only the (short, repeated) wire differs and is padded at the
# tap input on GRT RC, checked at TT AND FF.  The last stage drives the tap buffer.  Sinks are assigned to taps by the spec regions
# (first rectangle that contains the sink, else the nearest tap point).  Every structure cell is dont_touch and every
# structure net CLOCK + dont_touch, so resizer and TritonCTS leave them alone; clock_tree_synthesis is wrapped to run on
# the tap nets only (-clk_nets).  Functional netlist unchanged (buffers on the clock net only), SDC unchanged.
#
# Spec (OT_MSCTS_SPEC, a Tcl file):
#   set ot_ms_port ck                     ;# clock port
#   set ot_ms_root {x y}                  ;# root buffer site (um)
#   set ot_ms_taps { {NAME {x0 y0 x1 y1 ... xn yn} {{rx0 ry0 rx1 ry1} ...}} ... }
#        polyline starts at the root site and ends at the tap point; regions = sink rectangles of this tap
#   set ot_ms_macros { {INST_GLOB TAP {lx ly}} ... }   ;# macro clock leaf: tap whose trunk end feeds it, leaf site
# Knobs: OT_MSCTS_SEG_UM (45), OT_MSCTS_TRUNK_CELL (BUFx8_ASAP7_75t_R), OT_MSCTS_TAP_CELL (BUFx16f_ASAP7_75t_R),
#        OT_MSCTS_ROOT_CELL (BUFx16f_ASAP7_75t_R), OT_MSCTS_PAD_CELL (BUFx4_ASAP7_75t_R), OT_MSCTS_LEAF_CELL
#        (BUFx8_ASAP7_75t_R), OT_MSCTS_MACRO_PAD0 (initial macro delay-chain cells, 0), OT_MSCTS_WIN_PS (20),
#        OT_MSCTS_MACRO_TOL_PS (5), OT_MSCTS_ITERS (4), OT_MSCTS_PAD_PS (18, first pad-step guess), OT_MSCTS_HALO_UM (MACRO_ROWS_HALO_X or 4.32).
# Report lines: OT_MSCTS_BUILD / OT_MSCTS_TAP / OT_MSCTS_MACRO / OT_MSCTS_WINDOW (PASS|FAIL) / OT_MSCTS_TRUNK.

proc ot_ms_env {k d} { if {[info exists ::env($k)] && $::env($k) ne ""} { return $::env($k) }; return $d }
proc ot_ms_um {v} { return [expr {double($v) / [[ord::get_db_tech] getDbUnitsPerMicron]}] }
proc ot_ms_dbu {v} { return [expr {int(round($v * [[ord::get_db_tech] getDbUnitsPerMicron]))}] }

# macro + halo rectangles (um)
proc ot_ms_blocked_rects {} {
  set halo [ot_ms_env OT_MSCTS_HALO_UM [ot_ms_env MACRO_ROWS_HALO_X 4.32]]
  set r {}
  foreach i [[ord::get_db_block] getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set b [$i getBBox]
    lappend r [list [expr {[ot_ms_um [$b xMin]] - $halo}] [expr {[ot_ms_um [$b yMin]] - $halo}] \
                    [expr {[ot_ms_um [$b xMax]] + $halo}] [expr {[ot_ms_um [$b yMax]] + $halo}]]
  }
  return $r
}
# push a point out of any macro+halo rectangle (nearest edge), clamp to the core
proc ot_ms_free_pt {x y rects} {
  set core [[ord::get_db_block] getCoreArea]
  set cx0 [ot_ms_um [$core xMin]]; set cy0 [ot_ms_um [$core yMin]]; set cx1 [expr {[ot_ms_um [$core xMax]] - 3.0}]; set cy1 [expr {[ot_ms_um [$core yMax]] - 1.0}]
  foreach r $rects {
    lassign $r a0 b0 a1 b1
    if {$x > $a0 && $x < $a1 && $y > $b0 && $y < $b1} {
      set d [list [list [expr {$x - $a0}] [expr {$a0 - 1.5}] $y] [list [expr {$a1 - $x}] [expr {$a1 + 0.5}] $y] \
                  [list [expr {$y - $b0}] $x [expr {$b0 - 1.0}]] [list [expr {$b1 - $y}] $x [expr {$b1 + 0.5}]]]
      set best [lindex [lsort -real -index 0 $d] 0]
      puts "OT_MSCTS_WARN point ($x,$y) inside macro+halo -> ([lindex $best 1],[lindex $best 2])"
      set x [lindex $best 1]; set y [lindex $best 2]
    }
  }
  return [list [expr {min(max($x, $cx0), $cx1)}] [expr {min(max($y, $cy0), $cy1)}]]
}
proc ot_ms_polylen {pts} {
  set L 0.0
  for {set i 0} {$i + 3 < [llength $pts]} {incr i 2} {
    lassign [lrange $pts $i [expr {$i + 3}]] x0 y0 x1 y1
    set L [expr {$L + abs($x1 - $x0) + abs($y1 - $y0)}]
  }
  return $L
}
# point at arclength a along polyline pts
proc ot_ms_at {pts a} {
  set acc 0.0
  for {set i 0} {$i + 3 < [llength $pts]} {incr i 2} {
    lassign [lrange $pts $i [expr {$i + 3}]] x0 y0 x1 y1
    set l [expr {abs($x1 - $x0) + abs($y1 - $y0)}]
    if {$acc + $l >= $a - 1e-9} {
      set f [expr {$l > 0 ? ($a - $acc) / $l : 0.0}]
      # Manhattan leg: x first, then y
      set lx [expr {abs($x1 - $x0)}]; set d [expr {$f * $l}]
      if {$d <= $lx} { return [list [expr {$x0 + ($x1 >= $x0 ? $d : -$d)}] $y0] }
      set d [expr {$d - $lx}]
      return [list $x1 [expr {$y0 + ($y1 >= $y0 ? $d : -$d)}]]
    }
    set acc [expr {$acc + $l}]
  }
  return [lrange $pts end-1 end]
}
proc ot_ms_mk_inst {name master x y} {
  set blk [ord::get_db_block]
  set m [[ord::get_db] findMaster $master]; if {$m eq "NULL"} { error "OT_MSCTS: no master $master" }
  set i [odb::dbInst_create $blk $m $name]
  set rh [[lindex [$blk getRows] 0] getSite]; set rh [$rh getHeight]
  set core [$blk getCoreArea]
  set yd [ot_ms_dbu $y]; set yd [expr {[$core yMin] + int(round(double($yd - [$core yMin]) / $rh)) * $rh}]
  $i setLocation [expr {[ot_ms_dbu $x] - [$m getWidth] / 2}] $yd
  $i setPlacementStatus PLACED
  return $i
}
proc ot_ms_mk_net {name} { set n [odb::dbNet_create [ord::get_db_block] $name]; $n setSigType CLOCK; return $n }
proc ot_ms_conn {inst innet outnet} {
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    if {[$mt getSigType] in {POWER GROUND}} continue
    if {[$mt getIoType] eq "INPUT"} { $it connect $innet } elseif {[$mt getIoType] eq "OUTPUT"} { $it connect $outnet }
  }
}
# dont_touch on every structure cell and every structure net except the tap / macro-leaf nets (CTS owns the tap nets)
proc ot_ms_protect {on} {
  set blk [ord::get_db_block]
  foreach i [$blk getInsts] { if {[string match "ot_ms_*" [$i getName]]} { $i setDoNotTouch $on } }
  foreach n [$blk getNets] { if {[string match "ot_ms_*" [$n getName]] && ![regexp {^ot_ms_(.+)_clk$} [$n getName]]} { $n setDoNotTouch $on } }
}
proc ot_ms_in_rect {x y r} { lassign $r a0 b0 a1 b1; expr {$x >= $a0 && $x <= $a1 && $y >= $b0 && $y <= $b1} }

proc ot_ms_build {} {
  source $::env(OT_MSCTS_SPEC)
  upvar 0 ot_ms_port port ot_ms_root root ot_ms_taps taps ot_ms_macros macros
  set blk [ord::get_db_block]
  if {[$blk findInst ot_ms_root] ne "NULL"} { puts "OT_MSCTS_BUILD already built"; return }
  set seg [ot_ms_env OT_MSCTS_SEG_UM 45]
  set tcell [ot_ms_env OT_MSCTS_TRUNK_CELL BUFx8_ASAP7_75t_R]
  set tapcell [ot_ms_env OT_MSCTS_TAP_CELL BUFx16f_ASAP7_75t_R]
  set rcell [ot_ms_env OT_MSCTS_ROOT_CELL BUFx16f_ASAP7_75t_R]
  set lcell [ot_ms_env OT_MSCTS_LEAF_CELL BUFx8_ASAP7_75t_R]
  set pcell [ot_ms_env OT_MSCTS_PAD_CELL BUFx4_ASAP7_75t_R]
  set rects [ot_ms_blocked_rects]
  set bt [$blk findBTerm $port]; if {$bt eq "NULL"} { error "OT_MSCTS: no clock port $port" }
  set pnet [$bt getNet]
  # sinks of the port net (placement: no clock buffers yet)
  set sinks {}; set msinks {}
  foreach it [$pnet getITerms] {
    if {![$it isInputSignal] && [[$it getMTerm] getSigType] ne "CLOCK"} continue
    set i [$it getInst]
    if {[[$i getMaster] isBlock]} { lappend msinks $it; continue }
    set m [[$i getMaster] getName]
    if {[string match "BUF*" $m] || [string match "INV*" $m]} { error "OT_MSCTS: port net already buffered ([$i getName]); build runs on the placed netlist" }
    lappend sinks $it
  }
  # trunk geometry: equal stage count and stage length on every tap path
  set Lmax 0.0
  foreach t $taps { set Lmax [expr {max($Lmax, [ot_ms_polylen [lindex $t 1]])}] }
  set N [expr {max(1, int(ceil($Lmax / $seg)))}]
  lassign [ot_ms_free_pt {*}$root $rects] rx ry
  set rnet [ot_ms_mk_net ot_ms_root_n]
  set r [ot_ms_mk_inst ot_ms_root $rcell $rx $ry]; ot_ms_conn $r $pnet $rnet
  set ::ot_ms_tapnets {}; set ::ot_ms_tapinfo {}
  foreach t $taps {
    lassign $t name pts regs
    set L [ot_ms_polylen $pts]; set s [expr {$L / $N}]
    set prev $rnet
    for {set k 1} {$k <= $N} {incr k} {
      lassign [ot_ms_free_pt {*}[ot_ms_at $pts [expr {$k * $s}]] $rects] x y
      set n [ot_ms_mk_net ot_ms_${name}_t$k]
      set b [ot_ms_mk_inst ot_ms_${name}_s$k $tcell $x $y]; ot_ms_conn $b $prev $n
      set prev $n
    }
    # tap buffer at the last stage; local tree net under it
    set tnet [ot_ms_mk_net ot_ms_${name}_clk]
    set tb [ot_ms_mk_inst ot_ms_${name}_tap $tapcell $x $y]; ot_ms_conn $tb $prev $tnet
    lappend ::ot_ms_tapnets ot_ms_${name}_clk
    dict set ::ot_ms_tapinfo $name [list $x $y $regs ot_ms_${name}_t$N]
    puts [format "OT_MSCTS_TRUNK %s path %.1f um = %d stages x %.2f um, tap at (%.1f, %.1f)" $name $L $N $s $x $y]
  }
  # sink assignment
  set cnt {}
  foreach it $sinks {
    set bb [[$it getInst] getBBox]
    set x [ot_ms_um [expr {([$bb xMin] + [$bb xMax]) / 2}]]; set y [ot_ms_um [expr {([$bb yMin] + [$bb yMax]) / 2}]]
    set tap ""
    foreach t $taps { foreach rr [lindex $t 2] { if {$tap eq "" && [ot_ms_in_rect $x $y $rr]} { set tap [lindex $t 0] } } }
    if {$tap eq ""} {
      set bd 1e30
      dict for {nm inf} $::ot_ms_tapinfo { set d [expr {abs($x - [lindex $inf 0]) + abs($y - [lindex $inf 1])}]; if {$d < $bd} { set bd $d; set tap $nm } }
      dict incr cnt "${tap}_nearest"
    }
    $it disconnect; $it connect [$blk findNet ot_ms_${tap}_clk]
    dict incr cnt $tap
  }
  dict for {k v} $cnt { puts "OT_MSCTS_BUILD sinks $k $v" }
  # macro leaves: trunk end of the named tap -> pad chain -> leaf driver at the pin -> macro clk pin (one sink)
  set pad0 [ot_ms_env OT_MSCTS_MACRO_PAD0 0]
  set ::ot_ms_macleaf {}
  foreach it $msinks {
    set inst [$it getInst]; set iname [$inst getName]; set spec ""
    foreach mm $macros { if {[string match [lindex $mm 0] $iname]} { set spec $mm } }
    if {$spec eq ""} { error "OT_MSCTS: macro clock sink $iname has no ot_ms_macros entry" }
    lassign $spec glob tap site
    lassign [ot_ms_free_pt {*}$site $rects] lx ly
    set k [llength $::ot_ms_macleaf]
    set prev [$blk findNet [lindex [dict get $::ot_ms_tapinfo $tap] 3]]
    for {set j 0} {$j < $pad0} {incr j} {
      set n [ot_ms_mk_net ot_ms_m${k}_p$j]
      set b [ot_ms_mk_inst ot_ms_m${k}_pad$j $pcell [expr {$lx - 2.0 * ($pad0 - $j)}] $ly]; ot_ms_conn $b $prev $n
      set prev $n
    }
    set ln [ot_ms_mk_net ot_ms_m${k}_clk]
    set lb [ot_ms_mk_inst ot_ms_m${k}_leaf $lcell $lx $ly]; ot_ms_conn $lb $prev $ln
    $it disconnect; $it connect $ln
    lappend ::ot_ms_macleaf [list $iname $tap ot_ms_m${k}_leaf ot_ms_m${k}]
    puts "OT_MSCTS_BUILD macro $iname leaf ot_ms_m${k}_leaf at ($lx,$ly) from tap $tap trunk end, $pad0 pad cells"
  }
  # protect the structure: resizer / CTS never touch it
  ot_ms_protect 1
  set ::ot_ms_N $N
  puts [format "OT_MSCTS_BUILD taps %d trunk %d stages per tap (L_max %.1f um), root (%.1f, %.1f), %d register sinks, %d macro leaves" \
    [llength $taps] $N $Lmax $rx $ry [llength $sinks] [llength $::ot_ms_macleaf]]
  # TritonCTS builds the local trees under the tap nets only
  if {[info commands ot_ms_cts_orig] eq ""} {
    rename clock_tree_synthesis ot_ms_cts_orig
    proc clock_tree_synthesis {args} {
      set a {}
      for {set i 0} {$i < [llength $args]} {incr i} {
        if {[lindex $args $i] eq "-clk_nets"} { incr i; continue }
        lappend a [lindex $args $i]
      }
      lappend a -clk_nets $::ot_ms_tapnets
      puts "OT_MSCTS clock_tree_synthesis $a"
      uplevel 1 [list ot_ms_cts_orig {*}$a]
    }
  }
}

# ---------------------------------------------------------------------------------------------------------------------
# measurement: TT = max-rise clock arrival (slow corner of the session), FF = min-rise (fast corner)
proc ot_ms_regions {} {
  # tap -> list of sink clock pins (std-cell registers) found under the tap net through buffers
  set blk [ord::get_db_block]; set out {}
  foreach tn $::ot_ms_tapnets {
    set todo [list [$blk findNet $tn]]; set pins {}; set seen {}
    while {[llength $todo]} {
      set n [lindex $todo end]; set todo [lrange $todo 0 end-1]
      if {[dict exists $seen [$n getName]]} continue; dict set seen [$n getName] 1
      foreach it [$n getITerms] {
        if {![$it isInputSignal] && [[$it getMTerm] getSigType] ne "CLOCK"} continue
        set i [$it getInst]; set m [[$i getMaster] getName]
        if {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m] || [string match "HB*" $m]} {
          foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend todo [$o getNet] } }
        } else { lappend pins "[$i getName]/[[$it getMTerm] getName]" }
      }
    }
    dict set out [regsub {^ot_ms_(.*)_clk$} $tn {\1}] $pins
  }
  return $out
}
# STA clock-pin objects keyed by their name without escape backslashes (ODB and STA spell escaped names differently)
proc ot_ms_key {n} { return [string map {\\ {}} $n] }
proc ot_ms_pinmap {} {
  set ::ot_ms_pm {}
  foreach p [all_registers -clock_pins] { dict set ::ot_ms_pm [ot_ms_key [get_full_name $p]] $p }
}
proc ot_ms_arr {pin which} {
  if {![info exists ::ot_ms_pm]} { ot_ms_pinmap }
  set k [ot_ms_key $pin]
  if {![dict exists $::ot_ms_pm $k]} { return "" }
  set a ""; catch {set a [get_property [dict get $::ot_ms_pm $k] arrival_${which}_rise]}
  if {$a eq "" || ![string is double -strict $a]} { return "" }
  return $a
}
proc ot_ms_stats {pins which} {
  set v {}; foreach p $pins { set a [ot_ms_arr $p $which]; if {$a ne ""} { lappend v $a } }
  if {![llength $v]} { return {0 0 0 0} }
  set s 0.0; foreach a $v { set s [expr {$s + $a}] }
  set v [lsort -real $v]
  return [list [expr {$s / [llength $v]}] [lindex $v 0] [lindex $v end] [llength $v]]
}
# clock pin (name key) of a macro instance (ODB name)
proc ot_ms_macro_ck {iname} {
  if {![info exists ::ot_ms_pm]} { ot_ms_pinmap }
  foreach c {clk CLK} { set k "[ot_ms_key $iname]/$c"; if {[dict exists $::ot_ms_pm $k]} { return $k } }
  error "OT_MSCTS: no clock pin found for macro $iname"
}
# interface registers of a macro: launch registers of its data inputs + capture registers of its outputs
proc ot_ms_macro_if {iname} {
  if {![info exists ::ot_ms_pm]} { ot_ms_pinmap }
  set ck [dict get $::ot_ms_pm [ot_ms_macro_ck $iname]]
  set cell [get_cells -of_objects $ck]
  set ins {}; set outs {}
  foreach p [get_pins -of_objects $cell] {
    if {[ot_ms_key [get_full_name $p]] eq [ot_ms_key [get_full_name $ck]]} continue
    set d [get_property $p direction]
    if {$d eq "input"} { lappend ins $p } elseif {$d eq "output"} { lappend outs $p }
  }
  set regs {}
  if {[llength $ins]} { foreach x [get_fanin -to $ins -flat -startpoints_only -trace_arcs all] { lappend regs [ot_ms_key [regsub {/[^/]+$} [get_full_name $x] {}]] } }
  if {[llength $outs]} { foreach x [get_fanout -from $outs -flat -endpoints_only -trace_arcs all] { lappend regs [ot_ms_key [regsub {/[^/]+$} [get_full_name $x] {}]] } }
  set cks {}
  foreach r [lsort -unique $regs] {
    if {$r eq [ot_ms_key $iname]} continue
    foreach c {CLK clk} { if {[dict exists $::ot_ms_pm "$r/$c"]} { lappend cks "$r/$c"; break } }
  }
  return $cks
}

# ---------------------------------------------------------------------------------------------------------------------
# RCX CORRECTION (two-pass, OT_MSCTS_CORR): the GRT estimate of a long trunk is off by a per-path amount that no global RC
# scale removes (qfd_dv_s8x_vmr_cqb s5 pass 1: E trunk RCX -22.9 ps TT vs estimate, W1 +6.4: the wire C of a 41 um stage
# was 3.5 fF routed vs 6.8 estimated on the open east edge, 7.6 vs 6.3 in the congested west strip).  The trunk geometry
# is fixed by the spec, so the routed-minus-estimate arrival per tap (and per macro leaf) measured on a pass-1 route is a
# property of the structure: pass 2 balances est + correction (ot_ms_corr_*) and the FF hold step times the trunk at
# est + correction (ot_ms_assign_corr, set_assigned_delay on the trunk arcs).  File format (Tcl):
#   set ot_ms_corr     { TAP {tt_ps ff_ps} ... }          ;# RCX - estimate, tap-region mean arrival
#   set ot_ms_corr_mac { INST_GLOB {tt_ps ff_ps} ... }    ;# RCX - estimate, macro clock pin
proc ot_ms_corr_load {} {
  if {[info exists ::ot_ms_corr_loaded]} return
  set ::ot_ms_corr {}; set ::ot_ms_corr_mac {}
  set f [ot_ms_env OT_MSCTS_CORR ""]
  if {$f ne ""} { uplevel #0 [list source $f]; puts "OT_MSCTS_CORR $f taps $::ot_ms_corr macros $::ot_ms_corr_mac" }
  set ::ot_ms_corr_loaded 1
}
proc ot_ms_ctap {tap c} {
  ot_ms_corr_load
  if {[dict exists $::ot_ms_corr $tap]} { return [lindex [dict get $::ot_ms_corr $tap] [expr {$c eq "ff"}]] }
  return 0.0
}
proc ot_ms_cmac {iname c} {
  ot_ms_corr_load
  foreach {g v} $::ot_ms_corr_mac { if {[string match $g [ot_ms_key $iname]]} { return [lindex $v [expr {$c eq "ff"}]] } }
  return 0.0
}
# corrected mean arrival of a pin list (each pin corrected by the tap that drives it; R = ot_ms_regions)
proc ot_ms_cmean {pins which R c} {
  set t {}; dict for {tap ps} $R { foreach p $ps { dict set t [ot_ms_key $p] $tap } }
  set s 0.0; set n 0
  foreach p $pins {
    set a [ot_ms_arr $p $which]; if {$a eq ""} continue
    set k [ot_ms_key $p]; if {[dict exists $t $k]} { set a [expr {$a + [ot_ms_ctap [dict get $t $k] $c]}] }
    set s [expr {$s + $a}]; incr n
  }
  return [expr {$n ? $s / $n : 0.0}]
}
# FF/TT-only session: time the trunk at estimate + correction (spread evenly over the trunk stage + tap arcs of each
# path; the macro remainder on the macro leaf arc).  Call after estimate_parasitics; c = tt | ff.
proc ot_ms_assign_corr {c} {
  if {![info exists ::ot_ms_tapnets]} { ot_ms_recover }
  ot_ms_corr_load
  if {![llength $::ot_ms_corr] && ![llength $::ot_ms_corr_mac]} return
  if {![info exists ::ot_ms_macros]} { uplevel #0 [list source [ot_ms_env OT_MSCTS_SPEC ""]] }
  set ::ot_ms_assigned 1; set ::ot_ms_corr_trunk {}
  set blk [ord::get_db_block]
  set arcs {}
  dict for {tap v} $::ot_ms_corr {
    set st {}
    foreach i [$blk getInsts] { if {[regexp "^ot_ms_${tap}_s(\\d+)\$" [$i getName]]} { lappend st [$i getName] } }
    lappend st ot_ms_${tap}_tap
    set per [expr {[ot_ms_ctap $tap $c] / double([llength $st])}]
    foreach n $st { lappend arcs $n $per }
    dict set ::ot_ms_corr_trunk $tap [expr {$per * ([llength $st] - 1)}]
  }
  foreach ml $::ot_ms_macleaf {
    lassign $ml iname tap leaf pfx
    # tap of the leaf = the trunk the leaf hangs on (from the spec macro list)
    set t ""; foreach m $::ot_ms_macros { if {[string match [lindex $m 0] [ot_ms_key $iname]]} { set t [lindex $m 1] } }
    set tr [expr {$t ne "" && [dict exists $::ot_ms_corr_trunk $t] ? [dict get $::ot_ms_corr_trunk $t] : 0.0}]
    lappend arcs $leaf [expr {[ot_ms_cmac $iname $c] - $tr}]
  }
  foreach {n d} $arcs {
    set cell [get_cells $n]; set a ""; set y ""
    foreach p [get_pins -of_objects $cell] { if {[get_property $p direction] eq "input"} { set a $p } elseif {[get_property $p direction] eq "output"} { set y $p } }
    foreach rf {rise fall} {
      set da [get_property $y arrival_max_$rf]; set db [get_property $a arrival_max_$rf]
      set v [expr {$da - $db + $d}]
      if {$v < 1.0} { set v 1.0 }
      set_assigned_delay -cell -$rf -from $a -to $y $v
    }
  }
  puts [format "OT_MSCTS_ASSIGN_CORR %s %d arcs" $c [expr {[llength $arcs] / 2}]]
}

# balance: pad the early taps (tap input) and the macro leaves (pad chain) to the common latency
#   mode cts: placement RC (coarse); mode grt: GRT RC, global_route -start/-end_incremental around every edit
proc ot_ms_balance {mode} {
  if {![info exists ::ot_ms_tapnets]} { ot_ms_recover }
  set blk [ord::get_db_block]
  set win [ot_ms_env OT_MSCTS_WIN_PS 20]; set mtol [ot_ms_env OT_MSCTS_MACRO_TOL_PS 5]
  set iters [ot_ms_env OT_MSCTS_ITERS 4]; set pcell [ot_ms_env OT_MSCTS_PAD_CELL BUFx4_ASAP7_75t_R]
  set pm [[ord::get_db] findMaster $pcell]
  set_propagated_clock [all_clocks]
  if {![info exists ::ot_ms_padid]} { set ::ot_ms_padid 0 }
  set ifs {}
  foreach ml $::ot_ms_macleaf { dict set ifs [lindex $ml 0] [ot_ms_macro_if [lindex $ml 0]] }
  # pad step: one pad cell's measured delay (starts at OT_MSCTS_PAD_PS, 18; re-measured from every edit); the target is
  # the slowest tap of the first measurement and is never chased upward unless a tap overshoots it by > window / 2
  set dcell [ot_ms_env OT_MSCTS_PAD_PS 18.0]; set last {}; set tgt0 ""
  for {set it 0} {$it <= $iters} {incr it} {
    if {$mode eq "grt"} { estimate_parasitics -global_routing } else { estimate_parasitics -placement }
    ot_ms_pinmap
    set R [ot_ms_regions]
    set T {}; set hi -1e9; set lo 1e9
    dict for {tap pins} $R {
      set st [ot_ms_stats $pins max]; lset st 0 [expr {[lindex $st 0] + [ot_ms_ctap $tap tt]}]; dict set T $tap $st
      set hi [expr {max($hi, [lindex $st 0])}]; set lo [expr {min($lo, [lindex $st 0])}]
    }
    set M {}
    foreach ml $::ot_ms_macleaf {
      lassign $ml iname tap leaf pfx
      dict set M $leaf [list [expr {[ot_ms_arr [ot_ms_macro_ck $iname] max] + [ot_ms_cmac $iname tt]}] [ot_ms_cmean [dict get $ifs $iname] max $R tt]]
    }
    # re-measure the pad step from the previous edits
    set obs {}
    foreach {key was n} $last {
      lassign $key kind who
      set now [expr {$kind eq "tap" ? [lindex [dict get $T $who] 0] : [lindex [dict get $M $who] 0]}]
      lappend obs [expr {($now - $was) / double($n)}]
    }
    if {[llength $obs]} { set dcell [expr {min(40.0, max(8.0, [tcl::mathfunc::max {*}$obs]))}] }
    if {$tgt0 eq "" || $hi > $tgt0 + 0.5 * $win} { set tgt0 $hi }
    set tgt $tgt0
    set todo {}; set last {}
    dict for {tap st} $T {
      set gap [expr {$tgt - [lindex $st 0] - ($mode eq "cts" ? 5.0 : 0.0)}]
      set n [expr {int(round($gap / $dcell))}]
      if {$gap > 0.25 * $win && $n >= 1} { lappend todo [list tap $tap $n]; lappend last [list tap $tap] [lindex $st 0] $n }
    }
    dict for {leaf v} $M {
      lassign $v ma im
      set gap [expr {$im - $ma - ($mode eq "cts" ? 8.0 : 0.0)}]
      set n [expr {int(round($gap / $dcell))}]
      if {$gap > $mtol && $n >= 1} { lappend todo [list mac $leaf $n]; lappend last [list mac $leaf] $ma $n }
    }
    puts [format "OT_MSCTS_BAL %s iter %d tap means %.1f..%.1f (window %.1f) target %.1f pad step %.1f ps edits %s" $mode $it $lo $hi [expr {$hi - $lo}] $tgt $dcell $todo]
    if {![llength $todo] || $it == $iters} break
    if {$mode eq "grt"} { global_route -start_incremental }
    ot_ms_protect 0
    foreach e $todo {
      lassign $e kind who n
      if {$kind eq "tap"} { set ib [$blk findInst ot_ms_${who}_tap] } else { set ib [$blk findInst $who] }
      set in ""; foreach x [$ib getITerms] { if {[$x isInputSignal]} { set in $x } }
      set prev [$in getNet]; $in disconnect
      set loc [$ib getLocation]
      for {set j 0} {$j < $n} {incr j} {
        set nn [ot_ms_mk_net ot_ms_pad[incr ::ot_ms_padid]_n]
        set b [ot_ms_mk_inst ot_ms_pad${::ot_ms_padid} $pcell [expr {[ot_ms_um [lindex $loc 0]] - 1.0 - 1.2 * $j}] [ot_ms_um [lindex $loc 1]]]
        ot_ms_conn $b $prev $nn; set prev $nn
      }
      $in connect $prev
    }
    ot_ms_protect 1
    detailed_placement
    if {$mode eq "grt"} { global_route -end_incremental }
  }
  ot_ms_report $mode
}
proc ot_ms_report {mode} {
  if {![info exists ::ot_ms_tapnets]} { ot_ms_recover }
  set win [ot_ms_env OT_MSCTS_WIN_PS 20]; set mtol [ot_ms_env OT_MSCTS_MACRO_TOL_PS 5]
  set_propagated_clock [all_clocks]
  ot_ms_pinmap
  set R [ot_ms_regions]; set ok 1
  foreach w {max min} c {TT FF} {
    set hi -1e9; set lo 1e9
    set cc [string tolower $c]; set corr [expr {[ot_ms_env OT_MSCTS_CORR ""] ne "" && ![info exists ::ot_ms_assigned]}]
    dict for {tap pins} $R {
      lassign [ot_ms_stats $pins $w] mean mn mx n
      set k [expr {$corr ? [ot_ms_ctap $tap $cc] : 0.0}]
      puts [format "OT_MSCTS_TAP %s %s %s n %d mean %.1f min %.1f max %.1f%s" $mode $c $tap $n $mean $mn $mx [expr {$corr ? [format " | RCX-corrected mean %.1f" [expr {$mean + $k}]] : ""}]]
      set hi [expr {max($hi, $mean + $k)}]; set lo [expr {min($lo, $mean + $k)}]
    }
    set v [expr {$hi - $lo <= $win ? "PASS" : "FAIL"}]; if {$v ne "PASS"} { set ok 0 }
    puts [format "OT_MSCTS_WINDOW %s %s tap-mean window %.1f ps (limit %s) %s%s" $mode $c [expr {$hi - $lo}] $win $v [expr {$corr ? " (RCX-corrected)" : ""}]]
    foreach ml $::ot_ms_macleaf {
      lassign $ml iname tap leaf pfx
      set ma [expr {[ot_ms_arr [ot_ms_macro_ck $iname] $w] + ($corr ? [ot_ms_cmac $iname $cc] : 0.0)}]
      set ifp [ot_ms_macro_if $iname]
      lassign [ot_ms_stats $ifp $w] im imn imx inn
      if {$corr} { set im [ot_ms_cmean $ifp $w $R $cc] }
      puts [format "OT_MSCTS_MACRO %s %s %s clk %.1f interface regs n %d mean %.1f (%.1f..%.1f) diff %+.1f%s" $mode $c $iname $ma $inn $im $imn $imx [expr {$ma - $im}] [expr {$corr ? " (RCX-corrected)" : ""}]]
    }
  }
  return $ok
}
# a later stage (new process): rebuild the bookkeeping from the ot_ms_* names in the DB
proc ot_ms_recover {} {
  set blk [ord::get_db_block]
  set ::ot_ms_tapnets {}; set ::ot_ms_macleaf {}; set ::ot_ms_padid 0
  foreach n [$blk getNets] { if {[regexp {^ot_ms_(.+)_clk$} [$n getName] -> t] && ![regexp {^m[0-9]+$} $t]} { lappend ::ot_ms_tapnets [$n getName] } }
  foreach i [$blk getInsts] {
    set nm [$i getName]
    if {[regexp {^ot_ms_pad([0-9]+)$} $nm -> k]} { set ::ot_ms_padid [expr {max($::ot_ms_padid, $k)}] }
    if {[regexp {^ot_ms_m([0-9]+)_leaf$} $nm -> k]} {
      foreach it [$i getITerms] {
        if {[$it isOutputSignal]} { foreach s [[$it getNet] getITerms] { if {[[[$s getInst] getMaster] isBlock]} { lappend ::ot_ms_macleaf [list [[$s getInst] getName] ? $nm ot_ms_m$k] } } }
      }
    }
  }
  set ::ot_ms_tapnets [lsort $::ot_ms_tapnets]
}
