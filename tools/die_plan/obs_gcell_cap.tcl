# FLOW-OBS-GCELL-1121 (COORD; OPUS-FIX-HEAD-SERDES-R4 hd_host_e + hd_serdes sdr2c DRT-0255): GRT capacity 0 on the
# sliver gcells a routing obstruction leaves partly free.
# A reserved die-clock-site obstruction M1-M7 (337.338,345.06)-(339.498,346.41) covers 420 of the 570 nm of the GRT
# gcell row y 345.99-346.56; GRT still counts the 2 free M6 tracks above it (346.464, 346.528), routes a net there on
# M6, and DRT cannot use them inside its worker (DRT-0255 Maze Route cannot find path).  The track-lattice snap
# (OT_RESERVED_SNAP, 42fa174c180) keeps both tracks open, so it cannot cure this.
# For every dbObstruction on OT_OBS_GCELL_LAYERS (default M2-M7) that exists when grt_pre runs (before the temporary
# PG-track-truth / PGCAP guards), each gcell that the obstruction cuts ACROSS its tracks (an H-layer row its y edge falls
# in, a V-layer column its x edge falls in), over the obstruction's along-track span, keeps its capacity only when at
# least OT_OBS_GCELL_MIN_TRACKS (default 3) tracks of the real track grid stay DRT-legal there (wire + min spacing clear
# of every obstruction on the layer); otherwise set_global_routing_region_adjustment 1.0 sets that gcell to 0.
# A strip that holds a block pin (BTerm) shape on the layer is never cut (tap-pin escape columns keep their access).
# GRT-internal only: no DB shape changes, nothing to remove afterwards; DRT still sees the real obstruction.
# Gcell grid: origin 0, tile OT_OBS_GCELL_UM (default OT_PGCAP_GCELL_UM, else 0.57 um; GRT-0023 origin (0, 0));
# regions are whole gcells grown by OT_OBS_GCELL_EPS_DBU (default 10), the pg_pair_cap.tcl convention.
# OT_OBS_GCELL_CAP=0 switches the pass off.
proc ot_obsgc_env {name def} {
  if {[info exists ::env($name)] && $::env($name) ne ""} { return $::env($name) }
  return $def
}
# free (DRT-legal) tracks of one gcell: tracks sorted across positions, [lo, hi) the gcell across span, [a0, a1) its
# along span, obs {al0 ac0 al1 ac1} rects of the layer, clr = half width + min spacing
proc ot_obsgc_free {tracks lo hi a0 a1 obs clr} {
  set free 0
  foreach t $tracks {
    if {$t < $lo} continue
    if {$t >= $hi} break
    set blocked 0
    foreach q $obs {
      lassign $q p0 c0 p1 c1
      if {$p0 >= $a1 || $p1 <= $a0} continue
      if {$t + $clr > $c0 && $t - $clr < $c1} { set blocked 1; break }
    }
    if {!$blocked} { incr free }
  }
  return $free
}
# pure planner (no OpenROAD calls; test_obs_gcell_cap.py runs it in tclsh): returns {{ln al0 ac0 al1 ac1} ...} in
# gcell units (cut regions, along x across for the layer), plus a stats dict as the last element
proc ot_obsgc_plan {obsd tracksd pinsd clrd gc minfree} {
  set out {}; set ncand 0; set nexempt 0; set ncut 0
  dict for {ln obs} $obsd {
    set tracks [dict get $tracksd $ln]; set clr [dict get $clrd $ln]
    set pins {}; if {[dict exists $pinsd $ln]} { set pins [dict get $pinsd $ln] }
    array unset seen
    array unset bk
    set cut {}
    # bucket the layer's rects by along gcell index (a candidate only tests the rects in its own column)
    foreach q $obs {
      lassign $q p0 c0 p1 c1
      for {set i [expr {$p0 / $gc}]} {$i <= ($p1 - 1) / $gc} {incr i} { lappend bk($i) $q }
    }
    foreach o $obs {
      lassign $o al0 ac0 al1 ac1
      set i0 [expr {$al0 / $gc}]; set i1 [expr {($al1 - 1) / $gc}]
      set rows {}
      if {$ac0 % $gc != 0} { lappend rows [expr {$ac0 / $gc}] }
      if {$ac1 % $gc != 0 && [expr {$ac1 / $gc}] ni $rows} { lappend rows [expr {$ac1 / $gc}] }
      foreach r $rows {
        set lo [expr {$r * $gc}]; set hi [expr {($r + 1) * $gc}]
        set ex 0
        foreach p $pins {
          lassign $p p0 c0 p1 c1
          if {$p0 < ($i1 + 1) * $gc && $p1 > $i0 * $gc && $c0 < $hi && $c1 > $lo} { set ex 1; break }
        }
        for {set i $i0} {$i <= $i1} {incr i} {
          if {[info exists seen($i,$r)]} continue
          set seen($i,$r) 1; incr ncand
          if {$ex} { incr nexempt; continue }
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
proc ot_obsgc_add {} {
  if {[ot_obsgc_env OT_OBS_GCELL_CAP 1] eq "0"} { puts "OT_OBS_GCELL off (OT_OBS_GCELL_CAP=0)"; return }
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]; set u [$tech getDbUnitsPerMicron]
  set layers [ot_obsgc_env OT_OBS_GCELL_LAYERS {M2 M3 M4 M5 M6 M7}]
  set gcum [ot_obsgc_env OT_OBS_GCELL_UM [ot_obsgc_env OT_PGCAP_GCELL_UM 0.57]]
  set minfree [ot_obsgc_env OT_OBS_GCELL_MIN_TRACKS 3]
  set eps [ot_obsgc_env OT_OBS_GCELL_EPS_DBU 10]
  set gc [expr {int(round($gcum * $u))}]
  set die [$blk getDieArea]; set dx0 [$die xMin]; set dy0 [$die yMin]; set dx1 [$die xMax]; set dy1 [$die yMax]
  set obsd [dict create]; set tracksd [dict create]; set pinsd [dict create]; set clrd [dict create]; array set hor {}
  foreach ln $layers {
    set L [$tech findLayer $ln]
    if {$L eq "NULL" || $L eq ""} continue
    set hor($ln) [expr {[$L getDirection] eq "HORIZONTAL"}]
  }
  foreach o [$blk getObstructions] {
    set bb [$o getBBox]; set L [$bb getTechLayer]
    if {$L eq "NULL" || $L eq ""} continue
    set ln [$L getName]
    if {![info exists hor($ln)]} continue
    if {$hor($ln)} { dict lappend obsd $ln [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
    } else { dict lappend obsd $ln [list [$bb yMin] [$bb xMin] [$bb yMax] [$bb xMax]] }
  }
  if {[dict size $obsd] == 0} { puts "OT_OBS_GCELL no routing obstructions on $layers"; return }
  foreach bt [$blk getBTerms] { foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
    set L [$bx getTechLayer]; if {$L eq "NULL" || $L eq ""} continue
    set ln [$L getName]; if {![dict exists $obsd $ln]} continue
    if {$hor($ln)} { dict lappend pinsd $ln [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]
    } else { dict lappend pinsd $ln [list [$bx yMin] [$bx xMin] [$bx yMax] [$bx xMax]] }
  } } }
  dict for {ln obs} $obsd {
    set L [$tech findLayer $ln]; set tg [$blk findTrackGrid $L]
    if {$tg eq "NULL" || $tg eq ""} { dict unset obsd $ln; puts "OT_OBS_GCELL $ln has no track grid, skipped"; continue }
    dict set tracksd $ln [lsort -integer -unique [expr {$hor($ln) ? [$tg getGridY] : [$tg getGridX]}]]
    dict set clrd $ln [expr {([$L getWidth] + 1) / 2 + [$L getSpacing]}]
  }
  set plan [ot_obsgc_plan $obsd $tracksd $pinsd $clrd $gc $minfree]
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
  puts "OT_OBS_GCELL sliver gcells cut [dict get $st cut] of [dict get $st candidates] partly covered (pin-exempt [dict get $st exempt]); regions by layer [array get n]; errors $nerr (gcell_um $gcum min_tracks $minfree eps_dbu $eps layers $layers)"
}
