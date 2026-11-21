# FLOW-OBS-GCELL-1121 (COORD; OPUS-FIX-HEAD-SERDES-R4 hd_host_e + hd_serdes sdr2c DRT-0255): GRT capacity 0 on the
# sliver gcells a routing obstruction leaves partly free.
# A reserved die-clock-site obstruction M1-M7 (337.338,345.06)-(339.498,346.41) covers 420 of the 570 nm of the GRT
# gcell row y 345.99-346.56; GRT still counts the 2 free M6 tracks above it (346.464, 346.528), routes a net there on
# M6, and DRT cannot use them inside its worker (DRT-0255 Maze Route cannot find path).  The track-lattice snap
# (OT_RESERVED_SNAP, 42fa174c180) keeps both tracks open, so it cannot cure this.
# Sources (the shapes whose edges are examined): every dbObstruction on OT_OBS_GCELL_LAYERS (default M2-M7) except the
# temporary PG-track-truth / PGCAP guards (::ot_pgtt_obs), and the OBS shapes of placed block masters (macros, hard cores).
# Blockers (what a track must clear): the sources + the PG-track-truth guards + PG special wires on the layer.
# Each gcell a source cuts ACROSS its tracks (an H-layer row its y edge falls in, a V-layer column its x edge falls in),
# over the source's along-track span, keeps its capacity only when at least OT_OBS_GCELL_MIN_TRACKS (default 3) tracks
# of the real track grid stay DRT-legal there (wire + min spacing clear of every blocker); otherwise
# set_global_routing_region_adjustment 1.0 sets that gcell to 0.  Only the gcells a block pin (BTerm) or macro pin
# shape on the layer touches are exempt.
# GRT-internal only: no DB shape changes, nothing to remove afterwards; DRT still sees the real obstruction.  Region
# adjustments live in GlobalRouter, so a fresh incremental-GRT session re-applies this through grt_pg_replay.tcl.
# Gcell grid: origin 0, tile OT_OBS_GCELL_UM (default OT_PGCAP_GCELL_UM, else 0.57 um; GRT-0023 origin (0, 0));
# regions are whole gcells grown by OT_OBS_GCELL_EPS_DBU (default 10), the pg_pair_cap.tcl convention.
# OT_OBS_GCELL_CAP=0 switches the pass off.
proc ot_obsgc_env {name def} {
  if {[info exists ::env($name)] && $::env($name) ne ""} { return $::env($name) }
  return $def
}
# free (DRT-legal) tracks of one gcell: tracks sorted across positions, [lo, hi) the gcell across span, [a0, a1) its
# along span, obs {al0 ac0 al1 ac1 ?sp?} blocker rects of the layer (sp: the blocker's own width-based spacing, DRT treats an
# obstruction as wide metal), clr = half width + min spacing (the default when a blocker carries no sp)
proc ot_obsgc_free {tracks lo hi a0 a1 obs clr} {
  set free 0
  foreach t $tracks {
    if {$t < $lo} continue
    if {$t >= $hi} break
    set blocked 0
    foreach q $obs {
      lassign $q p0 c0 p1 c1 qc
      if {$p0 >= $a1 || $p1 <= $a0} continue
      if {$qc eq ""} { set qc $clr }
      if {$t + $qc > $c0 && $t - $qc < $c1} { set blocked 1; break }
    }
    if {!$blocked} { incr free }
  }
  return $free
}
# pure planner (no OpenROAD calls; test_obs_gcell_cap.py runs it in tclsh).  srcd / blkd / pinsd: {layer {rect ...}}
# in along/across coordinates (blkd = extra blockers beyond the sources).  Returns {{ln al0 ac0 al1 ac1} ...} in gcell
# units (cut regions), plus a stats dict as the last element.
proc ot_obsgc_plan {srcd blkd tracksd pinsd clrd gc minfree} {
  set out {}; set ncand 0; set nexempt 0; set ncut 0
  dict for {ln srcs} $srcd {
    set tracks [dict get $tracksd $ln]; set clr [dict get $clrd $ln]
    set pins {}; if {[dict exists $pinsd $ln]} { set pins [dict get $pinsd $ln] }
    set blk $srcs; if {[dict exists $blkd $ln]} { set blk [concat $srcs [dict get $blkd $ln]] }
    array unset seen; array unset bk; array unset pg
    set cut {}
    # bucket blockers by along gcell index (a candidate only tests the rects of its own column); pins by gcell
    foreach q $blk {
      lassign $q p0 c0 p1 c1
      for {set i [expr {$p0 / $gc}]} {$i <= ($p1 - 1) / $gc} {incr i} { lappend bk($i) $q }
    }
    foreach p $pins {
      lassign $p p0 c0 p1 c1
      for {set i [expr {$p0 / $gc}]} {$i <= ($p1 - 1) / $gc} {incr i} {
        for {set r [expr {$c0 / $gc}]} {$r <= ($c1 - 1) / $gc} {incr r} { set pg($i,$r) 1 }
      }
    }
    foreach o $srcs {
      lassign $o al0 ac0 al1 ac1
      set i0 [expr {$al0 / $gc}]; set i1 [expr {($al1 - 1) / $gc}]
      set rows {}
      if {$ac0 % $gc != 0} { lappend rows [expr {$ac0 / $gc}] }
      if {$ac1 % $gc != 0 && [expr {$ac1 / $gc}] ni $rows} { lappend rows [expr {$ac1 / $gc}] }
      foreach r $rows {
        set lo [expr {$r * $gc}]; set hi [expr {($r + 1) * $gc}]
        for {set i $i0} {$i <= $i1} {incr i} {
          if {[info exists seen($i,$r)]} continue
          set seen($i,$r) 1; incr ncand
          if {[info exists pg($i,$r)]} { incr nexempt; continue }
          if {[ot_obsgc_free $tracks $lo $hi [expr {$i * $gc}] [expr {($i + 1) * $gc}] $bk($i) $clr] < $minfree} {
            lappend cut [list $r $i]
          }
        }
      }
    }
    # merge runs of consecutive gcells in one row/column into one region
    set prev {}
    foreach rc [lsort -integer -index 0 [lsort -integer -index 1 [lsort -unique $cut]]] {
      lassign $rc r i
      incr ncut
      if {$prev ne "" && [lindex $prev 0] == $r && [lindex $prev 2] == $i - 1} {
        set prev [list $r [lindex $prev 1] $i]
      } else {
        if {$prev ne ""} { lappend out [list $ln [lindex $prev 1] [lindex $prev 0] [expr {[lindex $prev 2] + 1}] [expr {[lindex $prev 0] + 1}]] }
        set prev [list $r $i $i]
      }
    }
    if {$prev ne ""} { lappend out [list $ln [lindex $prev 1] [lindex $prev 0] [expr {[lindex $prev 2] + 1}] [expr {[lindex $prev 0] + 1}]] }
  }
  lappend out [dict create candidates $ncand exempt $nexempt cut $ncut]
  return $out
}
# master-frame rect -> placed rect (orientation about the master's own W x H frame, then the instance bbox origin)
proc ot_obsgc_xform {orient W H ox oy a b c d} {
  set pts {}
  foreach {x y} [list $a $b $c $d] {
    switch -- $orient {
      R0 { set p [list $x $y] }   R180 { set p [list [expr {$W-$x}] [expr {$H-$y}]] }
      MX { set p [list $x [expr {$H-$y}]] }   MY { set p [list [expr {$W-$x}] $y] }
      R90 { set p [list [expr {$H-$y}] $x] }   R270 { set p [list $y [expr {$W-$x}]] }
      MXR90 { set p [list $y $x] }   MYR90 { set p [list [expr {$H-$y}] [expr {$W-$x}]] }
      default { set p [list $x $y] }
    }
    lappend pts {*}$p
  }
  lassign $pts x0 y0 x1 y1
  return [list [expr {$ox + min($x0,$x1)}] [expr {$oy + min($y0,$y1)}] [expr {$ox + max($x0,$x1)}] [expr {$oy + max($y0,$y1)}]]
}
proc ot_obsgc_add {} {
  if {[ot_obsgc_env OT_OBS_GCELL_CAP 1] eq "0"} { puts "OT_OBS_GCELL off (OT_OBS_GCELL_CAP=0)"; return }
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]; set u [$tech getDbUnitsPerMicron]
  set layers [ot_obsgc_env OT_OBS_GCELL_LAYERS {M2 M3 M4 M5 M6 M7}]
  set gcum [ot_obsgc_env OT_OBS_GCELL_UM [ot_obsgc_env OT_PGCAP_GCELL_UM 0.57]]
  set minfree [ot_obsgc_env OT_OBS_GCELL_MIN_TRACKS 3]
  set eps [ot_obsgc_env OT_OBS_GCELL_EPS_DBU 10]
  set gc [expr {int(round($gcum * $u))}]
  set die [$blk getDieArea]; set dx0 [$die xMin]; set dy0 [$die yMin]; set dx1 [$die xMax]; set dy1 [$die yMax]
  set srcd [dict create]; set blkd [dict create]; set tracksd [dict create]; set pinsd [dict create]; set clrd [dict create]
  array set hor {}
  foreach ln $layers {
    set L [$tech findLayer $ln]
    if {$L eq "NULL" || $L eq ""} continue
    set hor($ln) [expr {[$L getDirection] eq "HORIZONTAL"}]
  }
  # rect in x/y -> along/across of the layer
  proc ot_obsgc_aa {h a b c d} { if {$h} { return [list $a $b $c $d] } else { return [list $b $a $d $c] } }
  array set tmp {}
  if {[info exists ::ot_pgtt_obs]} { foreach o $::ot_pgtt_obs { set tmp($o) 1 } }
  set nsrc 0; set nmac 0
  foreach o [$blk getObstructions] {
    set bb [$o getBBox]; set L [$bb getTechLayer]
    if {$L eq "NULL" || $L eq ""} continue
    set ln [$L getName]
    if {![info exists hor($ln)]} continue
    set r [ot_obsgc_aa $hor($ln) [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    if {[info exists tmp($o)]} { dict lappend blkd $ln $r } else { dict lappend srcd $ln $r; incr nsrc }
  }
  foreach bt [$blk getBTerms] { foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
    set L [$bx getTechLayer]; if {$L eq "NULL" || $L eq ""} continue
    set ln [$L getName]; if {![info exists hor($ln)]} continue
    dict lappend pinsd $ln [ot_obsgc_aa $hor($ln) [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]
  } } }
  # placed block masters: OBS shapes are sources, pin shapes exempt the gcells they touch
  foreach inst [$blk getInsts] {
    set m [$inst getMaster]
    if {![$m isBlock]} continue
    incr nmac
    set ib [$inst getBBox]; set ox [$ib xMin]; set oy [$ib yMin]
    set W [$m getWidth]; set H [$m getHeight]; set orient [$inst getOrient]
    foreach bx [$m getObstructions] {
      set L [$bx getTechLayer]; if {$L eq "NULL" || $L eq ""} continue
      set ln [$L getName]; if {![info exists hor($ln)]} continue
      dict lappend srcd $ln [ot_obsgc_aa $hor($ln) {*}[ot_obsgc_xform $orient $W $H $ox $oy [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]]
      incr nsrc
    }
    foreach mt [$m getMTerms] { foreach mp [$mt getMPins] { foreach bx [$mp getGeometry] {
      set L [$bx getTechLayer]; if {$L eq "NULL" || $L eq ""} continue
      set ln [$L getName]; if {![info exists hor($ln)]} continue
      dict lappend pinsd $ln [ot_obsgc_aa $hor($ln) {*}[ot_obsgc_xform $orient $W $H $ox $oy [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]]
    } } }
  }
  if {[dict size $srcd] == 0} { puts "OT_OBS_GCELL no routing obstructions on $layers"; return }
  # PG special wires block tracks too (DRT-legal count)
  foreach net [$blk getNets] {
    if {![$net isSpecial] || [$net getSigType] ni {POWER GROUND}} continue
    foreach sw [$net getSWires] { foreach w [$sw getWires] {
      if {[$w isVia]} continue
      set L [$w getTechLayer]; if {$L eq "NULL"} continue
      set ln [$L getName]; if {![dict exists $srcd $ln]} continue
      dict lappend blkd $ln [ot_obsgc_aa $hor($ln) [$w xMin] [$w yMin] [$w xMax] [$w yMax]]
    } }
  }
  # per-blocker clearance: half wire width + the layer spacing for the blocker's width (SPACINGTABLE PARALLELRUNLENGTH;
  # ASAP7 M2-M7: 0.072 um next to any shape wider than the minimum, so a reserved obstruction blocks the 1-2 tracks next to
  # its edge that GRT counts as free: host_e row 346.464 (38 nm from the edge) and sdr2c 34.776 (42 nm) are DRT-illegal)
  proc ot_obsgc_withsp {L rects} {
    set hw [expr {([$L getWidth] + 1) / 2}]; set out {}
    foreach r $rects {
      lassign $r p0 c0 p1 c1
      set w [expr {min($p1 - $p0, $c1 - $c0)}]; set len [expr {max($p1 - $p0, $c1 - $c0)}]
      set sp [$L getSpacing]
      if {![catch {$L getSpacing $w $len} wsp] && $wsp > $sp} { set sp $wsp }
      lappend out [list $p0 $c0 $p1 $c1 [expr {$hw + $sp}]]
    }
    return $out
  }
  set srcw [dict create]; set blkw [dict create]
  dict for {ln obs} $srcd { dict set srcw $ln [ot_obsgc_withsp [$tech findLayer $ln] $obs] }
  dict for {ln obs} $blkd { if {[dict exists $srcd $ln]} { dict set blkw $ln [ot_obsgc_withsp [$tech findLayer $ln] $obs] } }
  set srcd $srcw; set blkd $blkw
  dict for {ln obs} $srcd {
    set L [$tech findLayer $ln]; set tg [$blk findTrackGrid $L]
    if {$tg eq "NULL" || $tg eq ""} { dict unset srcd $ln; puts "OT_OBS_GCELL $ln has no track grid, skipped"; continue }
    dict set tracksd $ln [lsort -integer -unique [expr {$hor($ln) ? [$tg getGridY] : [$tg getGridX]}]]
    dict set clrd $ln [expr {([$L getWidth] + 1) / 2 + [$L getSpacing]}]
  }
  set plan [ot_obsgc_plan $srcd $blkd $tracksd $pinsd $clrd $gc $minfree]
  set st [lindex $plan end]
  array set n {}; set nerr 0
  foreach g [lrange $plan 0 end-1] {
    lassign $g ln a0 c0 a1 c1
    if {$hor($ln)} { set x0 $a0; set y0 $c0; set x1 $a1; set y1 $c1 } else { set x0 $c0; set y0 $a0; set x1 $c1; set y1 $a1 }
    set x0 [expr {max($dx0, $x0 * $gc - $eps)}]; set y0 [expr {max($dy0, $y0 * $gc - $eps)}]
    set x1 [expr {min($dx1, $x1 * $gc + $eps)}]; set y1 [expr {min($dy1, $y1 * $gc + $eps)}]
    if {[catch {set_global_routing_region_adjustment [list [expr {double($x0)/$u}] [expr {double($y0)/$u}] [expr {double($x1)/$u}] [expr {double($y1)/$u}]] -layer $ln -adjustment 1.0} err]} {
      puts "OT_OBS_GCELL error $ln: $err"; incr nerr; continue
    }
    if {![info exists n($ln)]} { set n($ln) 0 }; incr n($ln)
  }
  puts "OT_OBS_GCELL sliver gcells cut [dict get $st cut] of [dict get $st candidates] partly covered (pin-exempt [dict get $st exempt]); sources $nsrc (block masters $nmac); regions by layer [array get n]; errors $nerr (gcell_um $gcum min_tracks $minfree eps_dbu $eps layers $layers)"
}
