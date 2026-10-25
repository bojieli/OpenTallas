# S81/HEAD3 2026-10-25 (kit hook, sourced after relay_mid.tcl at PRE_GLOBAL_PLACE): anchor flop CHAINS on their routed
# path.  hd_tile prev10: the per-column-pair skew lines (u_pd1 -> u_pd -> u_l stages -> per-core tail copies, ~4.9k
# flops a pair) and B's raw-input copy line (u_xb1 -> ...) are pure flop chains between a FIXED source (the tile's
# input face flop u_bin_i) and FIXED sinks (A / B element pins).  Wirelength-driven GPL scattered them over the free
# area above the A cores (prev10: u_pd1 at (213,761), 490 um from its source, -198 ps; channel cell density only 13.6%).
# Here every chain is placed FIRM on an L path (vertical-then-horizontal or horizontal-then-vertical, whichever stays
# outside every hard-core halo) from its source to the centroid of its sinks: the head at the path corner (the
# channel mouth), the stages evenly along the last leg, the tail copies next to their own element pins.
# face_flops_release.tcl releases them to PLACED before DPL (names appended to ot_relay_mid.txt).
#   env OT_CHAIN_HEAD_RE  regex on the head flop name (backslashes removed), e.g. g_pair[.]g_pl\[[0-9]\][.]u_pd1/
uplevel #0 {
set ca_blk [ord::get_db_block]
set ca_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ca_re $::env(OT_CHAIN_HEAD_RE)
set ca_core [$ca_blk getCoreArea]
set ca_x0 [$ca_core xMin]; set ca_y0 [$ca_core yMin]; set ca_x1 [$ca_core xMax]; set ca_y1 [$ca_core yMax]
set ca_rows [$ca_blk getRows]
set ca_sw [[[lindex $ca_rows 0] getSite] getWidth]
set ca_rh [[[lindex $ca_rows 0] getSite] getHeight]
set ca_orient {}
foreach r $ca_rows { dict set ca_orient [lindex [$r getOrigin] 1] [$r getOrient] }
set ca_halo [expr {int(8.64 * $ca_dbu)}]
set ca_mac {}
foreach i [$ca_blk getInsts] {
  if {[[$i getMaster] isBlock]} {
    set b [$i getBBox]
    lappend ca_mac [list [expr {[$b xMin]-$ca_halo}] [expr {[$b yMin]-$ca_halo}] [expr {[$b xMax]+$ca_halo}] [expr {[$b yMax]+$ca_halo}]]
  }
}
proc ca_free {x y} {
  global ca_mac ca_x0 ca_y0 ca_x1 ca_y1
  if {$x < $ca_x0 || $y < $ca_y0 || $x > $ca_x1 || $y > $ca_y1} { return 0 }
  foreach m $ca_mac { lassign $m a b c d; if {$x > $a && $x < $c && $y > $b && $y < $d} { return 0 } }
  return 1
}
proc ca_seg_free {ax ay bx by} {
  global ca_dbu
  set n [expr {max(1, int((abs($bx - $ax) + abs($by - $ay)) / (2.0 * $ca_dbu)))}]
  for {set k 0} {$k <= $n} {incr k} {
    if {![ca_free [expr {$ax + ($bx - $ax) * $k / double($n)}] [expr {$ay + ($by - $ay) * $k / double($n)}]]} { return 0 }
  }
  return 1
}
proc ca_isbuf {inst} {
  set m [[$inst getMaster] getName]
  return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}]
}
proc ca_isff {inst} { return [expr {![[$inst getMaster] isBlock] && [string match "*DFF*" [[$inst getMaster] getName]]}] }
proc ca_ctr {b} { return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]] }
proc ca_out {inst} {
  foreach it [$inst getITerms] {
    if {[$it getSigType] eq "SIGNAL" && [[$it getMTerm] getIoType] eq "OUTPUT"} { return $it }
  }
  return ""
}
proc ca_din {inst} {
  foreach it [$inst getITerms] { if {[[$it getMTerm] getName] eq "D"} { return $it } }
  return ""
}
# loads of a net through <= 4 buffers / inverters: list of {F inst} (flop D) | {P x y} (fixed pin / port) | {X}
proc ca_loads {net depth} {
  set r {}
  if {$net eq "NULL" || $net eq "" || [$net getSigType] ne "SIGNAL"} { return $r }
  foreach bt [$net getBTerms] { lappend r [concat P [ca_ctr [$bt getBBox]]] }
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "INPUT"} continue
    set inst [$it getInst]
    if {[[$inst getMaster] isBlock]} { lappend r [concat P [ca_ctr [$it getBBox]]]; continue }
    if {[ca_isff $inst]} {
      if {[[$it getMTerm] getName] eq "D"} { lappend r [list F $inst] }
      continue
    }
    if {$depth < 4 && [ca_isbuf $inst]} {
      set o [ca_out $inst]
      if {$o ne ""} { set r [concat $r [ca_loads [$o getNet] [expr {$depth + 1}]]] }
      continue
    }
    lappend r X
  }
  return $r
}
# driver point of a net through <= 4 buffers / inverters: {x y} of a fixed driver, else {}
proc ca_drv {net depth} {
  if {$net eq "NULL" || $net eq ""} { return {} }
  foreach bt [$net getBTerms] { return [ca_ctr [$bt getBBox]] }
  foreach it [$net getITerms] {
    if {[[$it getMTerm] getIoType] ne "OUTPUT"} continue
    set inst [$it getInst]
    if {[[$inst getMaster] isBlock]} { return [ca_ctr [$it getBBox]] }
    if {$depth < 4 && [ca_isbuf $inst]} {
      foreach i2 [$inst getITerms] {
        if {[$i2 getSigType] eq "SIGNAL" && [[$i2 getMTerm] getIoType] eq "INPUT"} { return [ca_drv [$i2 getNet] [expr {$depth + 1}]] }
      }
    }
    if {[$inst getPlacementStatus] in {FIRM LOCKED}} { return [ca_ctr [$inst getBBox]] }
    return {}
  }
  return {}
}
proc ca_cent {pts} {
  set x 0.0; set y 0.0
  foreach p $pts { set x [expr {$x + [lindex $p 0]}]; set y [expr {$y + [lindex $p 1]}] }
  set n [llength $pts]
  return [list [expr {int($x / $n)}] [expr {int($y / $n)}]]
}
# nearest free point (rings of 2.16 um)
proc ca_near {x y} {
  global ca_dbu
  if {[ca_free $x $y]} { return [list $x $y] }
  set st [expr {int(2.16 * $ca_dbu)}]
  for {set r 1} {$r < 400} {incr r} {
    set d [expr {$r * $st}]
    foreach {dx dy} [list 0 $d 0 -$d $d 0 -$d 0 $d $d -$d $d $d -$d -$d -$d] {
      if {[ca_free [expr {$x + $dx}] [expr {$y + $dy}]]} { return [list [expr {$x + $dx}] [expr {$y + $dy}]] }
    }
  }
  return [list $x $y]
}
set ca_spot {}
set ca_out_f [open $::env(RESULTS_DIR)/ot_relay_mid.txt a]
set ca_log [open $::env(RESULTS_DIR)/ot_chain_anchor.txt w]
set ca_n 0; set ca_nchain 0; set ca_skip 0; set ca_seen {}
# Legal nearest-row packing. The previous bin-local cluster could overlap another
# bin's cluster, clip hundreds of cells to the same die-edge x, and move cells
# into macro halos after checking only the unshifted anchor. Reserve every exact
# footprint globally, including pre-existing face/relay registers.
set ca_occ {}
foreach i [$ca_blk getInsts] {
  if {[[$i getMaster] isBlock] || [$i getPlacementStatus] ni {FIRM LOCKED COVER}} continue
  set b [$i getBBox]
  set lo [expr {int(floor(double([$b yMin]-$ca_y0)/$ca_rh))}]
  set hi [expr {int(ceil(double([$b yMax]-$ca_y0)/$ca_rh))-1}]
  for {set row $lo} {$row <= $hi} {incr row} {
    dict lappend ca_occ $row [list [$b xMin] [$b xMax]]
  }
}
set ca_maxmove 0
set ca_hop_max 0; set ca_hop_bad 0
proc ca_put {c x y} {
  global ca_occ ca_sw ca_rh ca_x0 ca_y0 ca_x1 ca_y1 ca_orient ca_dbu ca_out_f ca_n ca_mac ca_maxmove ca_prev_xy
  set w [[$c getMaster] getWidth]
  set h [[$c getMaster] getHeight]
  set pad [expr {2*$ca_sw}]
  set r0 [expr {int(round(double($y-$ca_y0)/$ca_rh))}]
  set nr [expr {int(($ca_y1-$ca_y0-$h)/$ca_rh)}]
  set best {}; set cost 1e30
  for {set d 0} {$d <= $nr} {incr d} {
    if {$d*$ca_rh > $cost+$ca_rh} break
    foreach row [expr {$d == 0 ? [list $r0] : [list [expr {$r0-$d}] [expr {$r0+$d}]]}] {
      if {$row < 0 || $row > $nr} continue
      set cy [expr {$ca_y0+$row*$ca_rh}]
      set intervals {}
      set rend [expr {$row+int(ceil(double($h)/$ca_rh))-1}]
      for {set rr $row} {$rr <= $rend} {incr rr} {
        if {[dict exists $ca_occ $rr]} { set intervals [concat $intervals [dict get $ca_occ $rr]] }
      }
      foreach m $ca_mac {
        lassign $m mx0 my0 mx1 my1
        if {$cy < $my1 && $cy+$h > $my0} { lappend intervals [list $mx0 $mx1] }
      }
      lappend intervals [list $ca_x1 $ca_x1]
      set left $ca_x0
      foreach it [lsort -integer -index 0 $intervals] {
        lassign $it a b
        set right [expr {min($a-$pad,$ca_x1)}]
        set lo $left; set hi [expr {$right-$w}]
        # Bound the actual consecutive-register Manhattan hop, including legalisation.
        if {[info exists ca_prev_xy]} {
          lassign $ca_prev_xy px py
          set reach [expr {405*$ca_dbu-abs($cy+$h/2.0-$py)}]
          set lo [expr {max($lo,$px-$reach-$w/2.0)}]
          set hi [expr {min($hi,$px+$reach-$w/2.0)}]
        }
        if {$hi >= $lo} {
          set cx [expr {min(max($x,$lo),$hi)}]
          set cx [expr {$ca_x0+int(ceil(double($cx-$ca_x0)/$ca_sw))*$ca_sw}]
          if {$cx <= $hi} {
            set dd [expr {abs($cx-$x)+abs($cy-$y)}]
            if {$dd < $cost} { set best [list $cx $cy $row $rend]; set cost $dd }
          }
        }
        set left [expr {max($left,$b+$pad)}]
        if {$left+$w > $ca_x1} break
      }
    }
  }
  if {$best eq {}} { error "chain_anchor: no legal footprint for [$c getName]" }
  lassign $best cx cy row rend
  for {set rr $row} {$rr <= $rend} {incr rr} { dict lappend ca_occ $rr [list $cx [expr {$cx+$w}]] }
  if {[dict exists $ca_orient $cy]} { $c setOrient [dict get $ca_orient $cy] }
  $c setLocation $cx $cy
  $c setPlacementStatus FIRM
  puts $ca_out_f [$c getName]
  set ca_maxmove [expr {max($ca_maxmove,$cost)}]
  incr ca_n
}
foreach h [$ca_blk getInsts] {
  if {![ca_isff $h] || [$h getPlacementStatus] in {FIRM LOCKED COVER}} continue
  if {![regexp $ca_re [string map {\\ {}} [$h getName]]]} continue
  set d [ca_din $h]
  if {$d eq ""} { incr ca_skip; continue }
  set src [ca_drv [$d getNet] 0]
  if {$src eq {}} { incr ca_skip; continue }
  # walk the single-successor flop chain
  set chain [list $h]; set cur $h; set tail {}
  while {1} {
    set q [ca_out $cur]
    set ld [expr {$q eq "" ? {} : [ca_loads [$q getNet] 0]}]
    if {[llength $ld] == 1 && [lindex $ld 0 0] eq "F"} {
      set nx [lindex $ld 0 1]
      if {[$nx getPlacementStatus] in {FIRM LOCKED} || [dict exists $ca_seen [$nx getName]] || [llength $chain] > 400} { set tail $ld; break }
      lappend chain $nx; set cur $nx; continue
    }
    set tail $ld; break
  }
  # sinks: fixed points directly, or a tail flop's own fixed loads (per-core tail copies)
  set sinks {}; set tails {}; set bad 0
  foreach e $tail {
    switch [lindex $e 0] {
      P { lappend sinks [lrange $e 1 2] }
      F {
        set t [lindex $e 1]
        if {[$t getPlacementStatus] in {FIRM LOCKED}} { lappend sinks [ca_ctr [$t getBBox]]; continue }
        set tq [ca_out $t]
        set tp {}
        foreach e2 [expr {$tq eq "" ? {} : [ca_loads [$tq getNet] 0]}] { if {[lindex $e2 0] eq "P"} { lappend tp [lrange $e2 1 2] } }
        if {$tp eq {}} { incr bad; continue }
        lappend tails [list $t [ca_cent $tp]]
        lappend sinks [ca_cent $tp]
      }
      default { incr bad }
    }
  }
  if {$sinks eq {} || $bad > 0} { incr ca_skip; continue }
  lassign $src ax ay
  lassign [ca_cent $sinks] bx by
  # L path outside the halos: VH (corner ax,by) or HV (corner bx,ay); else straight
  if {[ca_seg_free $ax $ay $ax $by] && [ca_seg_free $ax $by $bx $by]} {
    set cx $ax; set cy $by
  } elseif {[ca_seg_free $ax $ay $bx $ay] && [ca_seg_free $bx $ay $bx $by]} {
    set cx $bx; set cy $ay
  } else {
    set cx $ax; set cy $ay
  }
  set n [llength $chain]
  set k 0
  set ca_prev_xy $src
  foreach c $chain {
    set f [expr {($k + 0.5) / double($n)}]
    ca_put $c [expr {int($cx + ($bx - $cx) * $f)}] [expr {int($cy + ($by - $cy) * $f)}]
    dict set ca_seen [$c getName] 1
    set ca_prev_xy [ca_ctr [$c getBBox]]
    incr k
  }
  set ca_tail_src $ca_prev_xy
  foreach t $tails {
    lassign $t ti tp
    if {[dict exists $ca_seen [$ti getName]]} continue
    set ca_prev_xy $ca_tail_src
    ca_put $ti {*}$tp
    dict set ca_seen [$ti getName] 1
  }
  set prev $src
  foreach c $chain {
    set pt [ca_ctr [$c getBBox]]
    set hop [expr {abs([lindex $pt 0]-[lindex $prev 0])+abs([lindex $pt 1]-[lindex $prev 1])}]
    set ca_hop_max [expr {max($ca_hop_max,$hop)}]
    if {$hop > 405*$ca_dbu} { incr ca_hop_bad }
    set prev $pt
  }
  foreach pt $sinks {
    set hop [expr {abs([lindex $pt 0]-[lindex $prev 0])+abs([lindex $pt 1]-[lindex $prev 1])}]
    set ca_hop_max [expr {max($ca_hop_max,$hop)}]
    if {$hop > 405*$ca_dbu} { incr ca_hop_bad }
  }
  incr ca_nchain
  puts $ca_log "[$h getName]\t$n\t[llength $tails]\t[expr {$ax/1000.0}],[expr {$ay/1000.0}]\t[expr {$cx/1000.0}],[expr {$cy/1000.0}]\t[expr {$bx/1000.0}],[expr {$by/1000.0}]"
}
close $ca_out_f; close $ca_log
puts "OT_CHAIN_ANCHOR placed $ca_n flops of $ca_nchain chains FIRM on L paths ($ca_skip heads skipped), placed max hop [expr {$ca_hop_max/double($ca_dbu)}] um, $ca_hop_bad hops >405 um, maximum legalisation displacement [expr {$ca_maxmove/double($ca_dbu)}] um"
}
