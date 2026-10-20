# Shared die-net repeater step (DIE-FLOW 2026-10-17; owner ruling HANDOFF 0cl, memory reach-405-repeaters-1016).
#
# One step for every die flow (S81 dietop_grt_sta, Qwen qwen_kv_die/chain grt.tcl, HBM die_case_v16, die_cluster
# cluster tops).  Sourced inside the caller's OpenROAD session after the die is placed and the libraries are read,
# before global_route.  Generated call: tools/die_repeaters/step.py (tcl_call / `step.py tcl`).
#
# What it does, and only this:
#   * repair_design on die nets with -max_wire_length MAX_WIRE (default 160 um: H-REACH measured an unrepeated hop
#     slew-limited at ~175 um at the native ot_inhold first cell; repeated BUFx8-class every ~160 um gives 600-750 um
#     per cycle) and set_max_transition = the native receiver input slew (default 260 ps, the closed views'
#     max_transition at the first native cell; a per-master table may only LOWER it).  The ETM pin models hide that
#     first cell, so the limit is set here, not taken from the ETM pins.
#   * buffers only (BUFx4..BUFx8 by default): every other lib cell is dont_use for the step (restored afterwards), so
#     the resizer can neither insert nor resize-into anything else -- never a register, never a hold cell.
#   * clock / reset distribution nets are untouched (dont_touch): every net on a register clock / clock lib pin, every
#     net whose odb sig type is CLOCK / POWER / GROUND or that is special, and the caller's name globs.
#   * relay stages unchanged by construction and CHECKED: every pre-existing instance survives with its master, every
#     new instance is an allowed buffer.  Any violation fails the step (caller exits non-zero).
#   * die nets longer than the die reach (planning defect: a missing relay register, standard 1) are measured before
#     repair from report_long_wires and reported; policy 'fail' makes them a step violation.
#   * legalisation of the new buffers: 'spread' (DIE-FLOW2 10-17, default; 'snap' is an alias): every new repeater is
#     put on its own free slot (rows x sites, never on a macro, a pre-existing cell or another repeater) of the nearest
#     density bin (bin_um, default 8.64 um) that is under the utilisation cap (spread_util, default 0.30) -- repeaters
#     spread over the channel instead of stacking at their ideal points (S81-DV p4e: 2.42M stacked repeaters -> GRT
#     overflow 5.96M M2/M3); then repair passes (repair_passes, default 1: a pass k>1 re-buffers data bits only and breaks forwarded-clock matching) re-run repair_design on the legal positions
#     and spread the new buffers again, so the displacement leaves no slew violator.  'dpl' (detailed_placement; small
#     dies only), or 'none' (caller legalises).
#   * post-GRT: ot_die_rep_post_grt_audit (called by every die flow after estimate_parasitics -global_routing) first
#     upsizes, in place, the repeaters driving post-GRT slew / cap violators (BUFx8 -> BUFx12f -> BUFx16f where the
#     footprint is free; post_grt_rounds, default 2; stage counts unchanged), then audits.
# Output: the JSON report (schema opentallas.die_repeaters.v1).  Returns the number of violations.

proc ot_die_rep_log {msg} { puts "OT_DIE_REP $msg"; flush stdout }

proc ot_die_rep_inst_map {blk} {
  set m [dict create]
  foreach inst [$blk getInsts] { dict set m [$inst getName] [[$inst getMaster] getName] }
  return $m
}

proc ot_die_rep_pin_net {blk pin} {
  set k [string last / $pin]
  if {$k > 0} {
    set inst [$blk findInst [string range $pin 0 [expr {$k - 1}]]]
    if {$inst eq "NULL" || $inst eq ""} { return "" }
    set it [$inst findITerm [string range $pin [expr {$k + 1}] end]]
    if {$it eq "NULL" || $it eq ""} { return "" }
    set n [$it getNet]
  } else {
    set bt [$blk findBTerm $pin]
    if {$bt eq "NULL" || $bt eq ""} { return "" }
    set n [$bt getNet]
  }
  if {$n eq "NULL" || $n eq ""} { return "" }
  return [$n getName]
}

proc ot_die_rep_json_str {s} { return "\"[string map {\\ \\\\ \" \\\"} $s]\"" }

# ---- spread legaliser (DIE-FLOW2 10-17).  insts: odb instances to place (new repeaters).  Each takes one slot (row x
# slot of the widest master) of the nearest bin with free capacity; a bin's capacity = util x its free slots (slots
# clear of the core edge, every hard macro and every other placed cell), filled in a stride order that spreads the
# cells over the bin.  Bins only fill, so the nearest-available ring of a source bin never shrinks (memo: fast).
# Two caps: the soft cap (util) is used within soft_rings bins of the ideal point; where the channel is full at the
# soft cap (dense relay channels), the hard cap (util_hard) from ring 0 outwards -- a denser channel instead of a
# long displacement (a repeater pushed ~300 um sideways re-creates the slew it was inserted to fix).
proc ot_die_rep_spread {insts report {util 0.30} {bin_um 8.64} {util_hard 0.60} {soft_rings 3}} {
  set t0 [clock seconds]
  set blk [ord::get_db_block]
  set dbu [$blk getDbUnitsPerMicron]
  set core [$blk getCoreArea]
  set cx0 [$core xMin]; set cy0 [$core yMin]; set cx1 [$core xMax]; set cy1 [$core yMax]
  set r0 [lindex [$blk getRows] 0]
  set site [$r0 getSite]; set sw [$site getWidth]; set rh [$site getHeight]
  lassign [$r0 getOrigin] rx0 ry0
  set ro0 [$r0 getOrient]; set ro1 [expr {$ro0 eq "R0" ? "MX" : "R0"}]
  if {![llength $insts]} {
    set f [open $report w]; puts $f "{\"schema\": \"opentallas.die_repeaters.spread.v1\", \"placed\": 0, \"unplaced\": 0}"; close $f
    return 0
  }
  set maxw 0; set mine [dict create]
  foreach inst $insts { set w [[$inst getMaster] getWidth]; if {$w > $maxw} { set maxw $w }; dict set mine [$inst getName] 1 }
  set slw [expr {(($maxw + $sw - 1) / $sw) * $sw}]
  if {[info exists ::ot_die_rep_slw]} { set slw $::ot_die_rep_slw } else { set ::ot_die_rep_slw $slw }
  set BR [expr {max(1, int(round($bin_um * $dbu / double($rh))))}]
  set BS [expr {max(1, int(round($bin_um * $dbu / double($slw))))}]
  # obstacles: every placed instance that is not one of ours (macros + pre-existing cells), coarse 200-um buckets
  set cb 200000; set obs {}
  array set ob {}
  foreach inst [$blk getInsts] {
    if {[dict exists $mine [$inst getName]]} { continue }
    if {![$inst isPlaced]} { continue }
    set bb [$inst getBBox]
    set m [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    set k [llength $obs]; lappend obs $m
    for {set i [expr {[lindex $m 0] / $cb}]} {$i <= [lindex $m 2] / $cb} {incr i} {
      for {set j [expr {[lindex $m 1] / $cb}]} {$j <= [lindex $m 3] / $cb} {incr j} { lappend ob($i,$j) $k }
    }
  }
  if {![info exists ::ot_die_rep_obs]} { set ::ot_die_rep_obs $obs; array set ::ot_die_rep_ob [array get ob] }
  if {![info exists ::ot_die_rep_occ]} { set ::ot_die_rep_occ [dict create] }
  array set cap {}; array set hcap {}; array set used {}; array set fl {}; array set memoS {}; array set memoH {}; set nhard 0; set onobs 0
  set nbins 0; set placed 0; set unplaced 0; set dsum 0.0; set dmax 0.0; set ringmax 0; set full 0
  set maxring [expr {int(4000.0 / $bin_um) + 1}]
  foreach inst $insts {
    set mst [$inst getMaster]; set w [$mst getWidth]; set h [$mst getHeight]
    set loc [$inst getLocation]
    set ix [expr {[lindex $loc 0] + $w / 2}]; set iy [expr {[lindex $loc 1] + $h / 2}]
    set gs [expr {($ix - $rx0) / $slw}]; set gr [expr {($iy - $ry0) / $rh}]
    set bi [expr {$gs / $BS}]; set bj [expr {$gr / $BR}]
    set got ""
    foreach hard {0 1} {
     if {$hard} { set lim $maxring; set d [expr {[info exists memoH($bi,$bj)] ? $memoH($bi,$bj) : 0}] } \
     else { set lim [expr {min($soft_rings, $maxring)}]; set d [expr {[info exists memoS($bi,$bj)] ? $memoS($bi,$bj) : 0}] }
     while {$got eq "" && $d <= $lim} {
      set best ""; set bd 1e30
      for {set di -$d} {$di <= $d} {incr di} {
        set step [expr {(abs($di) == $d) ? 1 : 2 * $d}]
        if {$step == 0} { set step 1 }
        for {set dj -$d} {$dj <= $d} {incr dj $step} {
          set b "[expr {$bi + $di}],[expr {$bj + $dj}]"
          if {![info exists cap($b)]} {
            # lazy bin init: free slots (row-major), capacity, stride order
            incr nbins
            set bx [expr {$bi + $di}]; set by [expr {$bj + $dj}]
            set s0 [expr {$bx * $BS}]; set g0 [expr {$by * $BR}]
            set xa [expr {$rx0 + $s0 * $slw}]; set xb [expr {$xa + $BS * $slw}]
            set ya [expr {$ry0 + $g0 * $rh}]; set yb [expr {$ya + $BR * $rh}]
            set near {}
            if {$xb > $cx0 && $xa < $cx1 && $yb > $cy0 && $ya < $cy1} {
              set seen [dict create]
              for {set i [expr {$xa / $cb}]} {$i <= $xb / $cb} {incr i} {
                for {set j [expr {$ya / $cb}]} {$j <= $yb / $cb} {incr j} {
                  if {![info exists ob($i,$j)]} { continue }
                  foreach k $ob($i,$j) {
                    if {[dict exists $seen $k]} { continue }; dict set seen $k 1
                    lassign [lindex $obs $k] ox0 oy0 ox1 oy1
                    if {$ox0 < $xb && $ox1 > $xa && $oy0 < $yb && $oy1 > $ya} { lappend near [list $ox0 $oy0 $ox1 $oy1] }
                  }
                }
              }
              set sl {}
              for {set r 0} {$r < $BR} {incr r} {
                set y [expr {$ya + $r * $rh}]
                if {$y < $cy0 || $y + $rh > $cy1} { continue }
                for {set c 0} {$c < $BS} {incr c} {
                  set x [expr {$xa + $c * $slw}]
                  if {$x < $cx0 || $x + $slw > $cx1} { continue }
                  set hit 0
                  foreach o $near {
                    lassign $o ox0 oy0 ox1 oy1
                    if {$x < $ox1 && $x + $slw > $ox0 && $y < $oy1 && $y + $rh > $oy0} { set hit 1; break }
                  }
                  if {!$hit} { lappend sl [list $x $y [expr {($g0 + $r) % 2}]] }
                }
              }
              set n [llength $sl]
            } else { set sl {}; set n 0 }
            set cap($b) [expr {$n ? max(1, int($util * $n + 0.5)) : 0}]
            set hcap($b) [expr {$n ? max($cap($b), int($util_hard * $n + 0.5)) : 0}]
            set used($b) 0
            if {$n > 1} {
              set st [expr {max(1, int($n * 0.381966))}]
              while {[ot_die_rep_gcd $st $n] != 1} { incr st }
              set o {}; for {set k 0} {$k < $hcap($b)} {incr k} { lappend o [lindex $sl [expr {($k * $st) % $n}]] }
              set fl($b) $o
            } else { set fl($b) $sl }
          }
          if {$used($b) >= ($hard ? $hcap($b) : $cap($b))} { continue }
          lassign [split $b ,] bx by
          set ddx [expr {($rx0 + ($bx * $BS + $BS / 2.0) * $slw) - $ix}]; set ddy [expr {($ry0 + ($by * $BR + $BR / 2.0) * $rh) - $iy}]
          set dd [expr {$ddx * $ddx + $ddy * $ddy}]
          if {$dd < $bd} { set bd $dd; set best $b }
        }
      }
      if {$best ne ""} { set got $best } else { incr d }
     }
     if {$hard} { set memoH($bi,$bj) $d } else { set memoS($bi,$bj) $d }
     if {$got ne ""} { if {$hard} { incr nhard }; break }
    }
    if {[info exists hcap($bi,$bj)] && $hcap($bi,$bj) == 0} { incr onobs }
    if {$got eq ""} { incr unplaced; continue }
    if {$d > $ringmax} { set ringmax $d }
    lassign [lindex $fl($got) $used($got)] x y odd
    incr used($got)
    if {$used($got) == $hcap($got)} { incr full }
    $inst setOrient [expr {$odd ? $ro1 : $ro0}]
    $inst setLocation $x $y
    $inst setPlacementStatus PLACED
    dict set ::ot_die_rep_occ "$x,$y" 1
    incr placed
    set dm [expr {(abs($x + $w / 2 - $ix) + abs($y + $h / 2 - $iy)) / double($dbu)}]
    set dsum [expr {$dsum + $dm}]; if {$dm > $dmax} { set dmax $dm }
  }
  if {![info exists ::ot_die_rep_onobs]} { set ::ot_die_rep_onobs 0 }
  incr ::ot_die_rep_onobs $onobs
  set f [open $report w]
  puts $f "{\"schema\": \"opentallas.die_repeaters.spread.v1\", \"placed\": $placed, \"unplaced\": $unplaced, \"util\": $util, \"util_hard\": $util_hard, \"soft_rings\": $soft_rings, \"placed_at_hard_cap\": $nhard, \"ideal_on_obstacle\": $onobs, \"bin_um\": $bin_um, \"slot_width_um\": [expr {$slw / double($dbu)}], \"bins_initialised\": $nbins, \"bins_full\": $full, \"max_ring\": $ringmax, \"mean_disp_um\": [format %.2f [expr {$placed ? $dsum / $placed : 0}]], \"max_disp_um\": [format %.2f $dmax], \"seconds\": [expr {[clock seconds] - $t0}]}"
  close $f
  if {![info exists ::ot_die_rep_maxdisp] || $dmax > $::ot_die_rep_maxdisp} { set ::ot_die_rep_maxdisp $dmax }
  ot_die_rep_log "spread placed=$placed unplaced=$unplaced util=$util/$util_hard hard=$nhard on_obstacle=$onobs bin_um=$bin_um bins=$nbins full=$full max_ring=$ringmax mean_disp_um=[format %.2f [expr {$placed ? $dsum / $placed : 0}]] max_disp_um=[format %.2f $dmax] s=[expr {[clock seconds] - $t0}]"
  return $unplaced
}

# Displacement WARNING (S81-DV 0cj (a), 10-17): a spread that moves a repeater more than half the max wire length away
# from its repair_design point leaves segments near or over the repeat length -- the signature of a plan lane running
# over a block (p4i: 7.5 mm of q/P.V lane over frame bodies, max_disp 322 um vs 51 on p4h, 1,402 post-GRT slew
# violators).  Warn, never fail: the post-GRT audit judges the actual slew.  -> "" or the warning text.
proc ot_die_rep_disp_warning {max_disp_um max_wire_um} {
  if {$max_wire_um <= 0 || $max_disp_um <= $max_wire_um / 2.0} { return "" }
  return [format "repeater displaced %.1f um > max_wire/2 = %.1f um by the spread: a die lane likely runs over a block (check the plan path; post-GRT slew decides)" $max_disp_um [expr {$max_wire_um / 2.0}]]
}

proc ot_die_rep_gcd {a b} { while {$b} { set t $b; set b [expr {$a % $b}]; set a $t }; return $a }

# ---- CORRIDOR placement + odb length census (S81-DIECHAIN 10-19).  The mu2/mu1/MAB die runs (2.82M BUFx8) left
# repair_design's buffers at Steiner ideal points; 311,924 sat on macro bodies and the spread moved them up to 841.8 um
# to the nearest free bin -- off the wire path, worst input slew 11,847 ps vs 260.  The corridor pass re-places every
# repeater of a pure buffer CHAIN (driver -> buf ... buf -> one sink: the die lane bits) on the free part of the
# chain's L-shaped Manhattan path (the side with less length over macro bodies), evenly spaced in free arc length, with
# the chain's stage count unchanged (forwarded-clock / data matching holds); the spread then only snaps each one to the
# nearest legal slot next to that point.  A path span over a macro body cannot hold a repeater: the resulting segment
# (free spacing + body span) is measured and reported per chain (> reach = a plan lane over a block, a planning defect).
#
# Pure geometry (no odb; tested with tclsh).  ivs: blocked intervals {a b}; returns merged, sorted, clipped to [lo, hi].
proc ot_die_rep_merge_iv {ivs lo hi} {
  set c {}
  foreach iv $ivs {
    lassign $iv a b
    if {$a > $b} { set t $a; set a $b; set b $t }
    if {$b <= $lo || $a >= $hi} { continue }
    lappend c [list [expr {max($a, $lo)}] [expr {min($b, $hi)}]]
  }
  set c [lsort -real -index 0 $c]
  set m {}
  foreach iv $c {
    if {[llength $m] && [lindex $iv 0] <= [lindex $m end 1]} {
      lset m end 1 [expr {max([lindex $m end 1], [lindex $iv 1])}]
    } else { lappend m $iv }
  }
  return $m
}

# legs: list of {xa ya xb yb blocked} (axis-parallel; blocked = merged intervals in leg distance from (xa,ya)).
# k repeaters -> {points max_seg blocked_len total_len}: points = k {x y} at free-arc fractions i/(k+1); max_seg = the
# longest path distance between consecutive stops (driver, repeaters, sink).  All-blocked path -> points {}.
proc ot_die_rep_corridor_targets {legs k} {
  set free {}; set s0 0.0; set blk 0.0
  foreach leg $legs {
    lassign $leg xa ya xb yb bl
    set len [expr {abs($xb - $xa) + abs($yb - $ya)}]
    set t 0.0
    foreach iv $bl {
      lassign $iv a b
      if {$a > $t} { lappend free [list [expr {$s0 + $t}] [expr {$s0 + $a}] $leg $s0] }
      set blk [expr {$blk + $b - $a}]; set t $b
    }
    if {$len > $t} { lappend free [list [expr {$s0 + $t}] [expr {$s0 + $len}] $leg $s0] }
    set s0 [expr {$s0 + $len}]
  }
  set L $s0; set F 0.0
  foreach f $free { set F [expr {$F + [lindex $f 1] - [lindex $f 0]}] }
  if {$k <= 0} { return [list {} $L $blk $L] }
  if {$F <= 0} { return [list {} $L $blk $L] }
  if {$blk <= 0} {
    set ss {}; for {set i 1} {$i <= $k} {incr i} { lappend ss [expr {$L * $i / double($k + 1)}] }
  } else {
    set iv {}; foreach f $free { lappend iv [list [lindex $f 0] [lindex $f 1]] }
    set key "$k|[expr {round($L)}]|$iv"
    if {[info exists ::ot_die_rep_smemo($key)]} { set ss $::ot_die_rep_smemo($key) } else {
      set ss [ot_die_rep_minmax_stops $iv $L $k]
      if {[array size ::ot_die_rep_smemo] < 200000} { set ::ot_die_rep_smemo($key) $ss }
    }
  }
  # S81-MU5 (10-19): a stop can fall outside every free interval (minmax_stops falls back to the segment start, e.g.
  # the driver at 0 on a macro body) -> mu4 die chain died with 'can't read "ls0"'.  Snap such a stop to the nearest
  # free point; ss is rewritten so max_seg is measured on the snapped stops.
  set pts {}; set ss2 {}
  foreach s $ss {
    set leg ""; set bd 1e30; set bleg ""; set bls0 0.0; set bs $s
    foreach f $free {
      lassign $f fa fb fl fs
      if {$s >= $fa - 1e-9 && $s <= $fb + 1e-9} { set leg $fl; set ls0 $fs; break }
      set c [expr {$s < $fa ? $fa : $fb}]
      if {abs($s - $c) < $bd} { set bd [expr {abs($s - $c)}]; set bleg $fl; set bls0 $fs; set bs $c }
    }
    if {$leg eq ""} { set leg $bleg; set ls0 $bls0; set s $bs }
    lappend ss2 $s
    lassign $leg xa ya xb yb
    set u [expr {$s - $ls0}]
    if {$xa != $xb} { set x [expr {$xa + ($xb > $xa ? $u : -$u)}]; set y $ya } else { set x $xa; set y [expr {$ya + ($yb > $ya ? $u : -$u)}] }
    lappend pts [list $x $y]
  }
  set ss [lsort -real $ss2]
  set prev 0.0; set mx 0.0
  foreach s [concat $ss [list $L]] { if {$s - $prev > $mx} { set mx [expr {$s - $prev}] }; set prev $s }
  return [list $pts $mx $blk $L]
}

# k stops on the free intervals iv (arc coords, sorted) of a path of length L that minimise the longest stop-to-stop
# segment (driver at 0, sink at L): binary search on the segment S with a greedy farthest-free-point feasibility walk;
# stops the greedy does not need split the longest segments (at the free point nearest their middle).
proc ot_die_rep_greedy_stops {iv L S} {
  set pos 0.0; set out {}
  while {$L - $pos > $S + 1e-9} {
    set t [expr {$pos + $S}]; set best ""
    foreach f $iv {
      lassign $f a b
      if {$a > $t} { break }
      if {$b <= $pos + 1e-9} { continue }
      set best [expr {min($b, $t)}]
    }
    if {$best eq "" || $best <= $pos + 1e-9} { return "" }
    lappend out $best; set pos $best
  }
  return $out
}
proc ot_die_rep_minmax_stops {iv L k} {
  set lo [expr {$L / double($k + 1)}]; set hi $L; set got [ot_die_rep_greedy_stops $iv $L $hi]
  for {set n 0} {$n < 24} {incr n} {
    set mid [expr {($lo + $hi) / 2.0}]
    set g [ot_die_rep_greedy_stops $iv $L $mid]
    if {$g ne "" && [llength $g] <= $k} { set hi $mid; set got $g } else { set lo $mid }
  }
  if {$got eq ""} { set got {} }
  while {[llength $got] < $k} {
    set stops [concat 0.0 $got [list $L]]; set bi -1; set bl -1
    for {set i 0} {$i < [llength $stops] - 1} {incr i} {
      set l [expr {[lindex $stops [expr {$i + 1}]] - [lindex $stops $i]}]
      if {$l > $bl} { set bl $l; set bi $i }
    }
    set a [lindex $stops $bi]; set b [lindex $stops [expr {$bi + 1}]]; set m [expr {($a + $b) / 2.0}]
    set p ""; set pd 1e30
    foreach f $iv {
      lassign $f fa fb
      set c [expr {min(max($m, $fa), $fb)}]
      if {$c <= $a || $c >= $b} { continue }
      if {abs($c - $m) < $pd} { set pd [expr {abs($c - $m)}]; set p $c }
    }
    if {$p eq ""} { set p $a }
    set got [lsort -real [concat $got [list $p]]]
  }
  return $got
}

# odb: macro (block-master) bodies of the pre-existing instances, indexed in bucket rows / columns (bucket um).
proc ot_die_rep_corr_index {blk {bucket_um 100.0}} {
  set dbu [$blk getDbUnitsPerMicron]; set B [expr {int($bucket_um * $dbu)}]
  array unset ::ot_die_rep_cy; array unset ::ot_die_rep_cx; array unset ::ot_die_rep_cmemo
  set ::ot_die_rep_cB $B; set n 0
  foreach inst [$blk getInsts] {
    if {![[$inst getMaster] isBlock]} { continue }
    set bb [$inst getBBox]
    set r [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    for {set j [expr {[lindex $r 1] / $B}]} {$j <= [lindex $r 3] / $B} {incr j} { lappend ::ot_die_rep_cy($j) $r }
    for {set i [expr {[lindex $r 0] / $B}]} {$i <= [lindex $r 2] / $B} {incr i} { lappend ::ot_die_rep_cx($i) $r }
    incr n
  }
  return $n
}

# blocked intervals (dbu, absolute coordinate along the line) of the horizontal line y (h) or vertical line x (v);
# memo per 1-um line key.
proc ot_die_rep_corr_line {hv c} {
  set key "$hv,[expr {$c / 1000}]"
  if {[info exists ::ot_die_rep_cmemo($key)]} { return $::ot_die_rep_cmemo($key) }
  set B $::ot_die_rep_cB; set iv {}
  if {$hv eq "h"} {
    if {[info exists ::ot_die_rep_cy([expr {$c / $B}])]} {
      foreach r $::ot_die_rep_cy([expr {$c / $B}]) { if {[lindex $r 1] < $c && [lindex $r 3] > $c} { lappend iv [list [lindex $r 0] [lindex $r 2]] } }
    }
  } else {
    if {[info exists ::ot_die_rep_cx([expr {$c / $B}])]} {
      foreach r $::ot_die_rep_cx([expr {$c / $B}]) { if {[lindex $r 0] < $c && [lindex $r 2] > $c} { lappend iv [list [lindex $r 1] [lindex $r 3]] } }
    }
  }
  set m [ot_die_rep_merge_iv $iv -1e18 1e18]
  set ::ot_die_rep_cmemo($key) $m
  return $m
}

# one axis-parallel leg (dbu) -> {xa ya xb yb blocked-in-leg-distance}
proc ot_die_rep_corr_leg {xa ya xb yb} {
  if {$ya == $yb} {
    set lo [expr {min($xa, $xb)}]; set hi [expr {max($xa, $xb)}]
    set m [ot_die_rep_merge_iv [ot_die_rep_corr_line h $ya] $lo $hi]
  } else {
    set lo [expr {min($ya, $yb)}]; set hi [expr {max($ya, $yb)}]
    set m [ot_die_rep_merge_iv [ot_die_rep_corr_line v $xa] $lo $hi]
  }
  set fwd [expr {($ya == $yb) ? ($xb >= $xa) : ($yb >= $ya)}]
  set a0 [expr {($ya == $yb) ? $xa : $ya}]
  set bl {}
  foreach iv $m {
    lassign $iv a b
    if {$fwd} { lappend bl [list [expr {$a - $a0}] [expr {$b - $a0}]] } else { lappend bl [list [expr {$a0 - $b}] [expr {$a0 - $a}]] }
  }
  if {!$fwd} { set bl [lsort -real -index 0 $bl] }
  return [list $xa $ya $xb $yb $bl]
}

proc ot_die_rep_iterm_xy {it} {
  if {[catch {set b [$it getBBox]}] || $b eq "" || $b eq "NULL"} { set b [[$it getInst] getBBox] }
  return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]]
}

proc ot_die_rep_net_drv_loads {net} {
  set drv ""; set loads {}
  foreach it [$net getITerms] {
    if {[$it isOutputSignal]} { set drv $it } elseif {[$it isInputSignal]} { lappend loads $it }
  }
  return [list $drv $loads]
}

# re-place the new repeaters `new` (odb insts) of pure chains on their corridors.  pre: dict of pre-existing inst names.
# -> dict of stats (chains, repeaters_moved, trees, all_blocked, max_seg_um, over_reach, over_wire, top).
proc ot_die_rep_corridor {blk new pre reach_um max_wire_um} {
  set t0 [clock seconds]
  set dbu [$blk getDbUnitsPerMicron]
  set nmac [ot_die_rep_corr_index $blk]
  set isnew [dict create]
  foreach inst $new { dict set isnew [$inst getName] 1 }
  set seen [dict create]
  set chains 0; set moved 0; set trees 0; set allb 0; set mx 0.0; set over 0; set overw 0; set top {}; set bterm_root 0
  foreach inst $new {
    set nm [$inst getName]
    if {[dict exists $seen $nm]} { continue }
    set ia [$inst findITerm A]
    if {$ia eq "NULL" || $ia eq ""} { continue }
    set n0 [$ia getNet]
    if {$n0 eq "NULL" || $n0 eq ""} { continue }
    lassign [ot_die_rep_net_drv_loads $n0] d0 l0
    # only start at the chain root: the input net's driver is a pre-existing instance (or a top port)
    if {$d0 ne "" && [dict exists $isnew [[$d0 getInst] getName]]} { continue }
    if {$d0 eq ""} { incr bterm_root; continue }
    # walk the chain from the root net
    set chain {}; set net $n0; set ok 1; set sink ""; set port 0
    while {1} {
      lassign [ot_die_rep_net_drv_loads $net] d ls
      if {[llength [$net getBTerms]]} { set ok 0; set port 1; break }
      if {[llength $ls] != 1} { set ok 0; break }
      set li [lindex $ls 0]; set lin [$li getInst]
      if {![dict exists $isnew [$lin getName]]} { set sink $li; break }
      lappend chain $lin; dict set seen [$lin getName] 1
      set yo [$lin findITerm Y]
      if {$yo eq "NULL" || $yo eq ""} { set ok 0; break }
      set net [$yo getNet]
      if {$net eq "NULL" || $net eq ""} { set ok 0; break }
    }
    if {$port} { incr bterm_root; continue }
    if {!$ok || $sink eq "" || ![llength $chain]} { incr trees; continue }
    lassign [ot_die_rep_iterm_xy $d0] x0 y0
    lassign [ot_die_rep_iterm_xy $sink] x1 y1
    set best ""
    foreach o {hv vh} {
      if {$o eq "hv"} { set legs [list [ot_die_rep_corr_leg $x0 $y0 $x1 $y0] [ot_die_rep_corr_leg $x1 $y0 $x1 $y1]] } \
      else { set legs [list [ot_die_rep_corr_leg $x0 $y0 $x0 $y1] [ot_die_rep_corr_leg $x0 $y1 $x1 $y1]] }
      set r [ot_die_rep_corridor_targets $legs [llength $chain]]
      if {$best eq "" || [lindex $r 1] < [lindex $best 1]} { set best $r }
    }
    incr chains
    lassign $best pts seg blkd L
    set seg_um [expr {$seg / double($dbu)}]
    if {![llength $pts]} { incr allb; continue }
    foreach b $chain p $pts {
      set m [$b getMaster]
      $b setLocation [expr {int([lindex $p 0]) - [$m getWidth] / 2}] [expr {int([lindex $p 1]) - [$m getHeight] / 2}]
      incr moved
    }
    if {$seg_um > $mx} { set mx $seg_um }
    if {$reach_um > 0 && $seg_um > $reach_um} {
      incr over
      if {[llength $top] < 200} { lappend top [list [$n0 getName] [format %.1f $seg_um] [format %.1f [expr {$blkd / double($dbu)}]] [format %.1f [expr {$L / double($dbu)}]]] }
    }
    if {$seg_um > 1.25 * $max_wire_um} { incr overw }
  }
  set top [lrange [lsort -real -decreasing -index 1 $top] 0 49]
  ot_die_rep_log "corridor macros=$nmac chains=$chains moved=$moved trees=$trees port_rooted=$bterm_root all_blocked=$allb max_seg_um=[format %.1f $mx] seg>reach($reach_um)=$over seg>1.25*max_wire=$overw s=[expr {[clock seconds] - $t0}]"
  return [dict create chains $chains moved $moved trees $trees port_rooted $bterm_root all_blocked $allb max_seg_um $mx over_reach $over over_wire $overw top $top]
}

# odb length census of every signal net not in skip: driver-to-farthest-sink Manhattan from the pin positions (real
# placed lengths; top-port nets are counted apart -- their unplaced die pins made report_long_wires' top 5,000 all
# port nets with steiner 0.0, so the mu2 census read longest 0 / overreach 0).  -> {scanned longest over port_nets}
# over = list of {net driver um} longer than limit_um (all of them, sorted, first 200 kept).
proc ot_die_rep_net_census {blk skip limit_um} {
  set dbu [$blk getDbUnitsPerMicron]
  set scanned 0; set longest 0.0; set over {}; set nover 0; set ports 0
  foreach net [$blk getNets] {
    set nm [$net getName]
    if {[dict exists $skip $nm]} { continue }
    if {[$net getSigType] ne "SIGNAL"} { continue }
    if {[llength [$net getBTerms]]} { incr ports; continue }
    lassign [ot_die_rep_net_drv_loads $net] d ls
    if {$d eq "" || ![llength $ls]} { continue }
    lassign [ot_die_rep_iterm_xy $d] x0 y0
    set m 0
    foreach l $ls { lassign [ot_die_rep_iterm_xy $l] x y; set v [expr {abs($x - $x0) + abs($y - $y0)}]; if {$v > $m} { set m $v } }
    incr scanned
    set um [expr {$m / double($dbu)}]
    if {$um > $longest} { set longest $um }
    if {$limit_um > 0 && $um > $limit_um} {
      incr nover
      if {[llength $over] < 2000} { lappend over [list $nm "[[$d getInst] getName]/[[$d getMTerm] getName]" [format %.1f $um]] }
    }
  }
  return [list $scanned $longest [lrange [lsort -real -decreasing -index 2 $over] 0 199] $ports $nover]
}

# instances of the block not named in dict `known` (the cells the last repair_design inserted)
proc ot_die_rep_new_insts {blk known} {
  set n {}
  foreach inst [$blk getInsts] { if {![dict exists $known [$inst getName]]} { lappend n $inst } }
  return $n
}

# buffers-only window: every other lib cell dont_use; returns the flagged list for ot_die_rep_restore_use
proc ot_die_rep_buffers_only {buffers} {
  set flagged {}
  foreach lc [get_lib_cells -quiet *] {
    if {[lsearch -exact $buffers [get_name $lc]] >= 0} { continue }
    if {![get_property $lc dont_use]} { lappend flagged $lc }
  }
  foreach lc $flagged { set_dont_use $lc }
  foreach b $buffers { unset_dont_use [get_lib_cells -quiet $b] }
  return $flagged
}
proc ot_die_rep_restore_use {flagged} { foreach lc $flagged { unset_dont_use $lc } }

# cfg: Tcl dict; keys (defaults): report (required), max_wire_um 160, slew_ps 260, receiver_slew {} (master ps ...),
# buffers {BUFx4_ASAP7_75t_R ...}, skip_nets {} (globs), repeat_nets {} (globs: forwarded-clock nets repeated WITH their
# data bits -- DIE-CLOCK accepts fclk repeaters matched to the data to +-1 stage; they override the clock skips), skip_sigtypes {CLOCK POWER GROUND}, skip_clock_pins 1,
# reach_um 0, over_reach report|fail, long_wire_scan 5000, rc_layer M4 ("" = keep caller's), repair_args "",
# legalize spread|snap(=spread)|dpl|none, spread_util 0.30, spread_util_hard 0.60, soft_rings 3, bin_um 8.64, repair_passes 1, slew_margin 0 (%), post_grt_rounds 2 (post-GRT upsizing), resize_cells {BUFx8 BUFx12f BUFx16f},
# bounds_tcl /work/cluster_bounds.tcl, libs {} (liberty files to read first), std_corner ""
# (TT|FF|SS: read the ASAP7 RVT std libs of that corner), design ""
proc ot_die_repeaters {cfg} {
  set t0 [clock seconds]
  set d [dict create max_wire_um 160 slew_ps 260 receiver_slew {} \
           buffers {BUFx4_ASAP7_75t_R BUFx4f_ASAP7_75t_R BUFx5_ASAP7_75t_R BUFx6f_ASAP7_75t_R BUFx8_ASAP7_75t_R} \
           skip_nets {} repeat_nets {} skip_sigtypes {CLOCK POWER GROUND} skip_clock_pins 1 reach_um 0 over_reach report \
           long_wire_scan 5000 post_drv report rc_layer M4 repair_args "" legalize spread bounds_tcl /work/cluster_bounds.tcl \
           libs {} std_corner "" design "" spread_util 0.30 spread_util_hard 0.60 soft_rings 3 bin_um 8.64 repair_passes 1 slew_margin 0 post_grt_rounds 2 \
           resize_cells {BUFx8_ASAP7_75t_R BUFx12f_ASAP7_75t_R BUFx16f_ASAP7_75t_R} corridor 0 post_reach report]
  set d [dict merge $d $cfg]
  dict with d {}
  if {![info exists report]} { error "ot_die_repeaters: cfg has no report path" }
  set viol 0; set notes {}
  foreach l $libs { if {![file exists $l]} { error "ot_die_repeaters: liberty missing $l" }; read_liberty $l }
  if {$std_corner ne ""} {
    foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${std_corner}_nldm_*.lib*] { read_liberty $l }
  }
  set blk [ord::get_db_block]
  foreach b $buffers { if {![llength [get_lib_cells -quiet $b]]} { error "ot_die_repeaters: buffer $b not in any liberty" } }

  # ---- pre-state
  set pre [ot_die_rep_inst_map $blk]
  set masters [lsort -unique [dict values $pre]]
  ot_die_rep_log "pre instances=[dict size $pre] masters=[llength $masters]"
  # fail closed: a master without liberty hides its pins from the resizer (its nets would silently stay unrepeated)
  set nolib {}
  foreach mst $masters {
    if {[llength [get_lib_cells -quiet $mst]]} { continue }
    set dm [[ord::get_db] findMaster $mst]; set nsig 0
    if {$dm ne "NULL" && $dm ne ""} { foreach mt [$dm getMTerms] { if {[$mt getSigType] eq "SIGNAL"} { incr nsig } } }
    if {$nsig > 0} { lappend nolib $mst }
  }
  if {[llength $nolib]} { incr viol [llength $nolib]; lappend notes "masters without liberty (nets invisible to repair): [lrange $nolib 0 19]" }

  # ---- native receiver slew: the global limit, lowered by any present master's own first-cell limit
  set slew $slew_ps; set slew_src default
  foreach {mst ps} $receiver_slew { if {[lsearch -exact $masters $mst] >= 0 && $ps < $slew} { set slew $ps; set slew_src $mst } }

  # ---- nets the step must not touch
  set skip [dict create]
  if {[llength $skip_nets]} { foreach n [get_nets -quiet $skip_nets] { dict set skip [get_full_name $n] glob } }
  set n_sig 0
  if {[llength $skip_sigtypes]} {
    foreach net [$blk getNets] {
      if {[$net isSpecial] || [lsearch -exact $skip_sigtypes [$net getSigType]] >= 0} { dict set skip [$net getName] sigtype; incr n_sig }
    }
  }
  set n_ck 0
  if {$skip_clock_pins} {
    set ckp [dict create]
    foreach mst $masters {
      set lc [lindex [get_lib_cells -quiet $mst] 0]
      if {$lc eq ""} { continue }
      set ps {}
      foreach lp [get_lib_pins -quiet -of_objects $lc] {
        set isck 0
        catch {set isck [expr {[get_property $lp is_register_clock] || [get_property $lp is_clock]}]}
        if {$isck} { lappend ps [get_name $lp] }
      }
      if {[llength $ps]} { dict set ckp $mst $ps }
    }
    foreach inst [$blk getInsts] {
      set mst [[$inst getMaster] getName]
      if {![dict exists $ckp $mst]} { continue }
      foreach p [dict get $ckp $mst] {
        set it [$inst findITerm $p]
        if {$it eq "NULL" || $it eq ""} { continue }
        set net [$it getNet]
        if {$net eq "NULL" || $net eq ""} { continue }
        if {![dict exists $skip [$net getName]]} { dict set skip [$net getName] clock_pin; incr n_ck }
      }
    }
  }
  set n_rep 0
  if {[llength $repeat_nets]} {
    # odb-name string match (as fclk_audit.tcl): sta get_nets globs miss bus-bit names ('n0_fck[0]'; S81-DV p4e: the
    # escaped glob matched 0 nets and every forwarded clock stayed unrepeated -> 42 fclk/data mismatches)
    dict for {nm why} $skip {
      if {$why eq "glob"} { continue }
      foreach g $repeat_nets { if {[string match $g $nm]} { dict unset skip $nm; incr n_rep; break } }
    }
    if {$n_rep == 0} { incr viol; lappend notes "repeat_nets {$repeat_nets} matched no clock-skipped net (forwarded clocks would stay unrepeated)" }
  }
  set skip_names [dict keys $skip]
  set ::ot_die_rep_skip $skip
  set fh [open [file rootname $report].skip_nets.txt w]; puts $fh [join $skip_names "\n"]; close $fh
  set dt {}
  # Q-DIE9 10-17: the escaped STA lookup misses bus-bit nets ('n_clk_r0[0]': dv2f11 matched 2 of 51 skip nets and
  # repair_design buffered 44 clock nets).  Every skip net is also marked do-not-touch on the odb net itself (the
  # resizer honours dbNet::isDoNotTouch), and the count reported is the odb count.
  foreach n $skip_names {
    set o [get_nets -quiet [string map {\[ \\[ \] \\]} $n]]
    if {![llength $o]} { set o [get_nets -quiet $n] }
    if {[llength $o]} { lappend dt {*}$o }
  }
  if {[llength $dt]} { set_dont_touch $dt }
  set n_dt_odb 0
  foreach n $skip_names {
    set net [$blk findNet $n]
    if {$net ne "NULL" && $net ne ""} { $net setDoNotTouch 1; incr n_dt_odb }
  }
  set dt [lrepeat $n_dt_odb x]
  set skip_iterms [dict create]
  foreach n $skip_names { set net [$blk findNet $n]; if {$net ne "NULL" && $net ne ""} { dict set skip_iterms $n [llength [$net getITerms]] } }
  ot_die_rep_log "skip nets=[llength $skip_names] (sigtype $n_sig, clock pins $n_ck; repeated forwarded clocks $n_rep) dont_touch=[llength $dt]"

  # ---- RC + limits
  if {$rc_layer ne ""} {
    source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
    set_wire_rc -signal -layer $rc_layer
  }
  set_max_transition $slew [current_design]
  estimate_parasitics -placement

  # ---- standard 1: die nets longer than the reach (no relay register) -- measured before any buffer goes in
  # odb census (S81-DIECHAIN 10-19): driver-to-farthest-sink Manhattan of every non-skip signal net from the placed pin
  # positions; top-port nets counted apart (report_long_wires' top N were all unplaced-port nets, steiner 0.0)
  set over {}; set longest 0.0; set scanned 0; set port_nets 0; set n_over 0
  if {$long_wire_scan > 0} {
    lassign [ot_die_rep_net_census $blk $skip $reach_um] scanned longest over port_nets n_over
    set fh [open [file rootname $report].long_wires.rpt w]
    puts $fh "# odb census pre-repair: net driver manhattan_um (> reach $reach_um um; $n_over nets, first 200)"
    foreach o $over { puts $fh [join $o " "] }
    close $fh
    ot_die_rep_log "long wires (odb census) scanned=$scanned port_nets=$port_nets longest_um=[format %.1f $longest] over_reach($reach_um)=$n_over"
    if {$n_over && $over_reach eq "fail"} { incr viol $n_over; lappend notes "over_reach nets: missing relay registers" }
  }

  # ---- buffers only: everything else dont_use for this step (restored after)
  set flagged [ot_die_rep_buffers_only $buffers]
  set r0 [clock seconds]
  set rcmd "repair_design -max_wire_length $max_wire_um -slew_margin $slew_margin -cap_margin $slew_margin $repair_args"
  set rc [catch {eval $rcmd} err]
  if {$rc} { ot_die_rep_restore_use $flagged; ot_die_rep_log "FAIL repair_design: $err"; error "ot_die_repeaters: repair_design: $err" }
  set repair_s [expr {[clock seconds] - $r0}]

  # ---- legalise the new buffers
  set ::ot_die_rep_corr {}; set legal "none"; set passes {}; set ::ot_die_rep_onobs 0; set ::ot_die_rep_maxdisp 0.0; set warnings {}
  if {$legalize eq "snap" || $legalize eq "spread"} {
    # spread (snap is an alias since DIE-FLOW2: the plain snap stacked every repeater at its ideal point).  Pass k > 1
    # re-runs repair_design on the legal positions (the spread displacement can leave long segments) and spreads again.
    set known $pre; set left 0
    for {set pass 1} {$pass <= $repair_passes} {incr pass} {
      set new [ot_die_rep_new_insts $blk $known]
      foreach inst $new { dict set known [$inst getName] [[$inst getMaster] getName] }
      if {$pass > 1 && ![llength $new]} { break }
      if {$pass == 1 && $corridor} { set ::ot_die_rep_corr [ot_die_rep_corridor $blk $new $pre $reach_um $max_wire_um] }
      incr left [ot_die_rep_spread $new [file rootname $report].spread$pass.json $spread_util $bin_um $spread_util_hard $soft_rings]
      lappend passes [llength $new]
      if {$pass == $repair_passes} { break }
      estimate_parasitics -placement
      if {[catch {eval $rcmd} err]} { ot_die_rep_restore_use $flagged; error "ot_die_repeaters: repair_design pass [expr {$pass + 1}]: $err" }
    }
    set new [ot_die_rep_new_insts $blk $known]
    if {[llength $new]} { incr left [ot_die_rep_spread $new [file rootname $report].spread_last.json $spread_util $bin_um $spread_util_hard $soft_rings]; lappend passes [llength $new] }
    set legal "spread util=$spread_util bin_um=$bin_um passes=[join $passes /] unplaced=$left"
    if {$left != 0} { incr viol $left; lappend notes "repeaters without a free slot: $left" }
    set w_ [ot_die_rep_disp_warning $::ot_die_rep_maxdisp $max_wire_um]
    if {$w_ ne ""} { lappend warnings $w_; ot_die_rep_log "WARNING $w_" }
  } elseif {$legalize eq "dpl"} {
    if {[catch {detailed_placement} e]} { incr viol; lappend notes "detailed_placement: $e"; set legal "dpl FAIL" } else { set legal dpl }
  }
  ot_die_rep_restore_use $flagged
  # post-legalisation census: every repeated segment (driver -> repeater -> ... -> sink) at its legal position
  set post_scanned 0; set post_longest 0.0; set post_over {}; set post_n_over 0
  if {$long_wire_scan > 0} {
    lassign [ot_die_rep_net_census $blk $skip $reach_um] post_scanned post_longest post_over _pp post_n_over
    set fh [open [file rootname $report].post_segments.rpt w]
    puts $fh "# odb census post-legalisation: net driver manhattan_um (> reach $reach_um um; $post_n_over nets, first 200)"
    foreach o $post_over { puts $fh [join $o " "] }
    close $fh
    ot_die_rep_log "post-legal segments scanned=$post_scanned longest_um=[format %.1f $post_longest] over_reach($reach_um)=$post_n_over"
    if {$post_n_over && $post_reach eq "fail"} { incr viol $post_n_over; lappend notes "repeated segments longer than the reach after legalisation (lane over a block / off corridor)" }
  }
  set ::ot_die_rep_cfg [dict create buffers $buffers max_wire_um $max_wire_um slew_margin $slew_margin repair_args $repair_args \
                          spread_util $spread_util spread_util_hard $spread_util_hard soft_rings $soft_rings bin_um $bin_um post_grt_rounds $post_grt_rounds resize_cells $resize_cells report $report]
  set ::ot_die_rep_pre $pre

  # ---- residual electrical audit on placement parasitics after repair + legalisation (every die net, not only the
  # repaired ones): pins still over the native max_transition / max_capacitance are listed; post_drv_policy fail
  # makes them violations (default report: GRT parasitics + die STA are the sign-off)
  estimate_parasitics -placement
  set drvf [file rootname $report].post_drv.rpt
  report_check_types -max_slew -max_capacitance -violators > $drvf
  set fh [open $drvf]; set drvtxt [read $fh]; close $fh
  set post_slew 0; set post_cap 0; set post_skipped 0; set sec ""; set drv_top {}
  foreach line [split $drvtxt "\n"] {
    if {[string match -nocase "*max slew*" $line]} { set sec slew; continue }
    if {[string match -nocase "*max capacitance*" $line]} { set sec cap; continue }
    if {[regexp {^(\S+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+\(VIOLATED\)} $line -> pin lim val slk]} {
      if {[dict exists $skip [ot_die_rep_pin_net $blk $pin]]} { incr post_skipped; continue }
      if {$sec eq "slew"} { incr post_slew } elseif {$sec eq "cap"} { incr post_cap }
      if {[llength $drv_top] < 50} { lappend drv_top [list $sec $pin $lim $val] }
    }
  }
  if {($post_slew || $post_cap) && $post_drv eq "fail"} { incr viol [expr {$post_slew + $post_cap}]; lappend notes "residual max slew / cap violators after repair" }
  ot_die_rep_log "post-repair violators slew=$post_slew cap=$post_cap (on untouched clock/reset/skip nets: $post_skipped)"

  # ---- post-state checks: relay stages / registers unchanged, buffers only, skip nets untouched
  set post [ot_die_rep_inst_map $blk]
  set removed 0; set changed 0; set bad_new 0; set by_master [dict create]; set examples {}
  dict for {n m} $pre {
    if {![dict exists $post $n]} { incr removed; if {[llength $examples] < 10} { lappend examples "removed $n" } } \
    elseif {[dict get $post $n] ne $m} { incr changed; if {[llength $examples] < 10} { lappend examples "resized $n $m->[dict get $post $n]" } }
  }
  dict for {n m} $post {
    if {[dict exists $pre $n]} { continue }
    dict incr by_master $m
    if {[lsearch -exact $buffers $m] < 0} { incr bad_new; if {[llength $examples] < 10} { lappend examples "inserted $n $m" } }
  }
  set skip_changed 0
  dict for {n c} $skip_iterms { set net [$blk findNet $n]; if {$net eq "NULL" || $net eq "" || [llength [$net getITerms]] != $c} { incr skip_changed } }
  set repeaters [expr {[dict size $post] - [dict size $pre] + $removed}]
  incr viol [expr {$removed + $changed + $bad_new + $skip_changed}]
  if {$removed} { lappend notes "pre-existing instances removed" }
  if {$changed} { lappend notes "pre-existing instances resized (registers / relay stages must stay unchanged)" }
  if {$bad_new} { lappend notes "non-buffer cells inserted" }
  if {$skip_changed} { lappend notes "clock/reset/skip nets modified" }
  set verdict [expr {$viol == 0 ? "PASS" : "FAIL"}]

  set f [open $report w]
  set bm {}; dict for {m c} $by_master { lappend bm "[ot_die_rep_json_str $m]: $c" }
  set ov {}; foreach o [lrange [lsort -real -decreasing -index 2 $over] 0 49] { lappend ov "\[[ot_die_rep_json_str [lindex $o 0]], [ot_die_rep_json_str [lindex $o 1]], [lindex $o 2]\]" }
  set nt {}; foreach n $notes { lappend nt [ot_die_rep_json_str $n] }
  set wn {}; foreach n $warnings { lappend wn [ot_die_rep_json_str $n] }
  set ex {}; foreach n $examples { lappend ex [ot_die_rep_json_str $n] }
  puts $f "{\"schema\": \"opentallas.die_repeaters.v1\", \"design\": [ot_die_rep_json_str $design], \"verdict\": \"$verdict\", \"violations\": $viol,"
  puts $f " \"rule\": \"repair_design on die nets only, buffers only, between relay registers; one repeater from ~175 um then every ~160 um (owner 0cl, H-REACH)\","
  puts $f " \"max_wire_um\": $max_wire_um, \"max_transition_ps\": $slew, \"max_transition_source\": [ot_die_rep_json_str $slew_src], \"rc_layer\": [ot_die_rep_json_str $rc_layer],"
  puts $f " \"repair_args\": [ot_die_rep_json_str $repair_args], \"legalize\": [ot_die_rep_json_str $legal], \"repeaters_ideal_on_obstacle\": $::ot_die_rep_onobs, \"on_obstacle_note\": \"repair_design put these on a macro / relay body: the net crosses a block (plan path over a block, routed on M7+ or detoured) -- a planning defect, the spread moves them to the nearest free channel\","
  puts $f " \"instances_pre\": [dict size $pre], \"instances_post\": [dict size $post], \"repeaters\": $repeaters, \"repeaters_by_master\": {[join $bm {, }]},"
  puts $f " \"removed\": $removed, \"resized\": $changed, \"non_buffer_inserted\": $bad_new, \"skip_nets\": [llength $skip_names], \"skip_nets_modified\": $skip_changed,"
  puts $f " \"skip_by\": {\"sigtype\": $n_sig, \"clock_pin\": $n_ck, \"glob\": [expr {[llength $skip_names] - $n_sig - $n_ck + $n_rep}]}, \"repeated_clock_nets\": $n_rep, \"masters_without_liberty\": [llength $nolib],"
  puts $f " \"reach_um\": $reach_um, \"over_reach_policy\": [ot_die_rep_json_str $over_reach], \"long_wires_scanned\": $scanned, \"longest_um\": $longest, \"over_reach_nets\": $n_over, \"port_nets_excluded\": $port_nets, \"over_reach_top\": \[[join $ov {, }]\],"
  set ct {}; set cs {}
  if {[llength $::ot_die_rep_corr]} {
    foreach o [dict get $::ot_die_rep_corr top] { lappend ct "\[[ot_die_rep_json_str [lindex $o 0]], [lindex $o 1], [lindex $o 2], [lindex $o 3]\]" }
    foreach k {chains moved trees port_rooted all_blocked over_reach over_wire} { lappend cs "\"$k\": [dict get $::ot_die_rep_corr $k]" }
    lappend cs "\"max_seg_um\": [format %.2f [dict get $::ot_die_rep_corr max_seg_um]]"
  }
  set po {}; foreach o [lrange $post_over 0 49] { lappend po "\[[ot_die_rep_json_str [lindex $o 0]], [ot_die_rep_json_str [lindex $o 1]], [lindex $o 2]\]" }
  puts $f " \"corridor\": $corridor, \"corridor_stats\": {[join $cs {, }]}, \"corridor_over_reach_top\": \[[join $ct {, }]\],"
  puts $f " \"post_reach_policy\": [ot_die_rep_json_str $post_reach], \"post_segments_scanned\": $post_scanned, \"post_longest_segment_um\": [format %.2f $post_longest], \"post_segments_over_reach\": $post_n_over, \"post_segments_over_reach_top\": \[[join $po {, }]\],"
  set dt_ {}; foreach o $drv_top { lappend dt_ "\[[ot_die_rep_json_str [lindex $o 0]], [ot_die_rep_json_str [lindex $o 1]], [ot_die_rep_json_str [lindex $o 2]], [ot_die_rep_json_str [lindex $o 3]]\]" }
  puts $f " \"post_drv_policy\": [ot_die_rep_json_str $post_drv], \"post_slew_violators\": $post_slew, \"post_cap_violators\": $post_cap, \"post_violators_on_skip_nets\": $post_skipped, \"post_drv_top\": \[[join $dt_ {, }]\],"
  puts $f " \"spread_max_disp_um\": [format %.2f $::ot_die_rep_maxdisp], \"warnings\": \[[join $wn {, }]\], \"notes\": \[[join $nt {, }]\], \"examples\": \[[join $ex {, }]\], \"repair_s\": $repair_s, \"seconds\": [expr {[clock seconds] - $t0}]}"
  close $f
  ot_die_rep_log "$verdict repeaters=$repeaters violations=$viol over_reach=$n_over post_seg_over_reach=$post_n_over legalize=($legal) s=[expr {[clock seconds] - $t0}]"
  return $viol
}

# Post-GRT electrical audit (DIE-FLOW 10-17, after the d4f region run: the placement-estimate audit was clean while GRT
# detours at dense relay pin faces left 4,754 slew violators).  Call after estimate_parasitics -global_routing (same
# session as the step, or a later STA session with skip_file = <report>.skip_nets.txt).  Writes REPORT (JSON) and
# returns the number of violators on repeated die nets (pins on untouched clock/reset nets are counted apart).
# Post-GRT upsizing (same session as the step, after global_route + estimate_parasitics -global_routing).  The
# driver of every residual slew / cap violator that is a step repeater is swapped in place to the next cell of the
# resize ladder (resize_cells, default BUFx12f, BUFx16f) when the wider footprint lands on free slots (no other
# repeater, macro or pre-existing cell): stage counts are unchanged (forwarded-clock matching holds), routes stay.
# (repair_design under GRT parasitics -- the ORFS post-GRT re-buffer -- ran past 64 GB on a 94-mm2 die-top pilot
# that otherwise peaks at 4.4 GB, so the step does not re-buffer after GRT.)  Returns the cells resized.
proc ot_die_rep_post_grt_resize {pins} {
  set c $::ot_die_rep_cfg
  set blk [ord::get_db_block]; set db [ord::get_db]
  set core [$blk getCoreArea]; set cx1 [$core xMax]
  set slw $::ot_die_rep_slw; set cb 200000
  set ladder [dict get $c resize_cells]
  set done [dict create]; set n 0; set blocked 0; set notrep 0; set top 0
  foreach pin $pins {
    set net [ot_die_rep_pin_net $blk $pin]
    if {$net eq ""} { continue }
    set drv ""
    foreach it [[$blk findNet $net] getITerms] { if {[$it isOutputSignal]} { set drv [$it getInst]; break } }
    if {$drv eq "" || [dict exists $::ot_die_rep_pre [$drv getName]]} { incr notrep; continue }
    if {[dict exists $done [$drv getName]]} { continue }
    dict set done [$drv getName] 1
    set cur [[$drv getMaster] getName]
    set k [lsearch -exact $ladder $cur]
    set nxt [lindex $ladder [expr {$k + 1}]]
    if {$nxt eq ""} { incr top; continue }
    set m [$db findMaster $nxt]
    if {$m eq "NULL" || $m eq ""} { incr top; continue }
    lassign [$drv getLocation] x y
    set x1 [expr {$x + [$m getWidth]}]; set y1 [expr {$y + [$m getHeight]}]
    set ok [expr {$x1 <= $cx1}]
    set xo [expr {$x + [[$drv getMaster] getWidth]}]
    for {set sx [expr {$x + $slw}]} {$ok && $sx < $x1} {incr sx $slw} { if {$sx >= $xo && [dict exists $::ot_die_rep_occ "$sx,$y"]} { set ok 0 } }
    for {set i [expr {$x / $cb}]} {$ok && $i <= $x1 / $cb} {incr i} {
      for {set j [expr {$y / $cb}]} {$ok && $j <= $y1 / $cb} {incr j} {
        if {![info exists ::ot_die_rep_ob($i,$j)]} { continue }
        foreach q $::ot_die_rep_ob($i,$j) {
          lassign [lindex $::ot_die_rep_obs $q] ox0 oy0 ox1 oy1
          if {$x < $ox1 && $x1 > $ox0 && $y < $oy1 && $y1 > $oy0} { set ok 0; break }
        }
      }
    }
    if {!$ok} { incr blocked; continue }
    replace_cell [get_cells [string map {\[ \\[ \] \\]} [$drv getName]]] $nxt
    for {set sx [expr {$x + $slw}]} {$sx < $x1} {incr sx $slw} { dict set ::ot_die_rep_occ "$sx,$y" 1 }
    incr n
  }
  estimate_parasitics -global_routing
  ot_die_rep_log "post-GRT resize: resized=$n blocked=$blocked driver_not_a_repeater=$notrep at_ladder_top=$top"
  return [list $n $blocked $notrep $top]
}

proc ot_die_rep_post_grt_audit {report {skip_file ""}} {
  set blk [ord::get_db_block]
  set rounds {}
  if {[info exists ::ot_die_rep_cfg] && [dict get $::ot_die_rep_cfg post_grt_rounds] > 0} {
    set pre_rpt [file rootname $report].pre_repair.rpt
    for {set k 1} {$k <= [dict get $::ot_die_rep_cfg post_grt_rounds]} {incr k} {
      report_check_types -max_slew -max_capacitance -violators > $pre_rpt
      set fh [open $pre_rpt]; set txt [read $fh]; close $fh
      set vp {}
      foreach line [split $txt "\n"] {
        if {[regexp {^(\S+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+\(VIOLATED\)} $line -> pin]} {
          if {![dict exists $::ot_die_rep_skip [ot_die_rep_pin_net $blk $pin]]} { lappend vp $pin }
        }
      }
      if {![llength $vp]} { break }
      lassign [ot_die_rep_post_grt_resize $vp] added blocked notrep top
      lappend rounds "\{\"round\": $k, \"violators_before\": [llength $vp], \"resized\": $added, \"blocked\": $blocked, \"driver_not_a_repeater\": $notrep, \"at_ladder_top\": $top\}"
      if {$added <= 0} { break }
    }
  }
  # resizing keeps stage counts; re-audit anyway when cells changed (forwarded clocks matched to their data (DIE-CLOCK +-1 stage): re-audit when it added cells
  set fclk_post -1
  if {[llength $rounds] && [info exists ::ot_die_rep_fclk_args] && [llength [info procs ot_die_rep_fclk_audit]]} {
    set fclk_post [ot_die_rep_fclk_audit {*}$::ot_die_rep_fclk_args]
  }
  # pre-existing instances (registers / relay stages) must survive the re-buffer unchanged
  set pg_bad 0
  if {[info exists ::ot_die_rep_pre]} {
    dict for {n m} $::ot_die_rep_pre { set i [$blk findInst $n]; if {$i eq "NULL" || $i eq "" || [[$i getMaster] getName] ne $m} { incr pg_bad } }
  }
  if {[info exists ::ot_die_rep_skip]} { set skip $::ot_die_rep_skip } else { set skip [dict create] }
  if {$skip_file ne "" && [file exists $skip_file]} {
    set fh [open $skip_file]; foreach n [split [string trim [read $fh]] "\n"] { if {$n ne ""} { dict set skip $n file } }; close $fh
  }
  set rpt [file rootname $report].rpt
  report_check_types -max_slew -max_capacitance -violators > $rpt
  set fh [open $rpt]; set txt [read $fh]; close $fh
  set sl 0; set cp 0; set sk 0; set sec ""; set worst 0.0; set top {}
  foreach line [split $txt "\n"] {
    if {[string match -nocase "*max slew*" $line]} { set sec slew; continue }
    if {[string match -nocase "*max capacitance*" $line]} { set sec cap; continue }
    if {[regexp {^(\S+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+(-?[0-9.]+)\s+\(VIOLATED\)} $line -> pin lim val slk]} {
      if {[dict exists $skip [ot_die_rep_pin_net $blk $pin]]} { incr sk; continue }
      if {$sec eq "slew"} { incr sl; if {$val > $worst} { set worst $val } } elseif {$sec eq "cap"} { incr cp }
      if {[llength $top] < 50} { lappend top "\[[ot_die_rep_json_str $sec], [ot_die_rep_json_str $pin], $lim, $val\]" }
    }
  }
  set f [open $report w]
  puts $f "{\"schema\": \"opentallas.die_repeaters.post_grt.v1\", \"verdict\": \"[expr {$sl + $cp + $pg_bad + max($fclk_post, 0) == 0 ? "PASS" : "FAIL"}]\", \"rebuffer_rounds\": \[[join $rounds {, }]\], \"fclk_mismatch_after_rebuffer\": $fclk_post, \"pre_existing_changed\": $pg_bad, \"slew_violators\": $sl, \"cap_violators\": $cp, \"worst_slew_ps\": $worst, \"on_skip_nets\": $sk, \"top\": \[[join $top {, }]\]}"
  close $f
  ot_die_rep_log "post-GRT violators slew=$sl cap=$cp worst_slew=$worst (on untouched clock/reset/skip nets: $sk)"
  return [expr {$sl + $cp + $pg_bad + max($fclk_post, 0)}]
}
