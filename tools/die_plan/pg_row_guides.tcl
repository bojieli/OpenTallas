# pg_row_guides.tcl (PG-ROW-GUIDES-1, FABLE-FIX-S81-SERDES2 2026-11-17; DRT-0255 class A of FABLE-PD-DRT-1350): move GRT guides off the PG pair rows.
# Class: FastRoute's layer assignment still lays horizontal M6 guides along a gcell row covered by the M6 VSS/VDD pair, in the
# obstruction form AND in the region form of pg_track_truth (serdes__t13 H15, region mode: 286 such segments, 9.0 mm; H5, obstruction
# form: 216).  The row has 0 or 1 DRT-legal track of that layer, detail route drops the trunk to M4 under the pair / M8 over it and the
# first optimization iteration dies with DRT-0255 where a worker edge cuts that wire.
# Form: sourced as PRE_DETAIL_ROUTE (the design is loaded from 5_1_grt.odb, before detailed_route).  For every routing layer in
# OT_PG_ROW_GUIDES_LAYERS (default M6) a gcell row (column for a vertical layer) is BAD when at most OT_PG_ROW_GUIDES_MIN_TRACKS
# (default 1) of its tracks are spacing-legal against the PG stripes of that layer.  Every guide of that layer that is one gcell wide,
# lies in a BAD row and is at least OT_PG_ROW_GUIDES_MIN_GCELLS (default 2) long is moved to the nearest row that is not BAD
# (at most 3 rows away; a row that no stripe of the layer touches is preferred).  Each guide of the same net on the layer itself or an adjacent layer that touched the old box gets a
# connector guide on its own layer over the gcells between the old and the new row, so the guide graph stays connected.
# Same nets, cells, pins, PG and timing constraints: only dbGuide boxes change.  Wrapped in catch: on any error the guides of the
# net being edited may be partly moved but stay connected (connectors are created before the old guide is destroyed).
# Proof (serdes__t13, H15 GRT DB, stock iteration table): 236 bad rows, 105 guides on 98 nets moved; violations 97814 -> 18598 after
# iteration 1 where six forms without the move died.  OT_PG_ROW_GUIDES=0 turns it off.
namespace eval pgrg {}
proc pgrg::env {n d} { if {[info exists ::env($n)] && $::env($n) ne ""} { return $::env($n) }; return $d }
proc pgrg::rect {x0 y0 x1 y1} {
  if {![catch {odb::new_Rect $x0 $y0 $x1 $y1} r]} { return $r }
  return [odb::Rect $x0 $y0 $x1 $y1]
}
proc pgrg::mk {net layer g x0 y0 x1 y1} {
  # same via layer / congestion flag as the guide it derives from
  odb::dbGuide_create $net $layer [$g getViaLayer] [pgrg::rect $x0 $y0 $x1 $y1] [$g isCongested]
}
# number of tracks of the sorted grid g inside [a, b) whose wire (half width hw) keeps spacing sp to every stripe span {lo hi}
proc pgrg::legal_tracks {g a b spans hw sp} {
  set legal 0
  set k [expr {[lsearch -sorted -integer -bisect $g [expr {$a - 1}]] + 1}]
  for {} {$k < [llength $g]} {incr k} { set t [lindex $g $k]; if {$t >= $b} break
    set ok 1
    foreach s $spans { lassign $s lo hi; if {$t + $hw + $sp > $lo && $t - $hw - $sp < $hi} { set ok 0; break } }
    incr legal $ok }
  return $legal
}
# bad rows of one layer: dict row index -> 1
proc pgrg::bad_rows {blk L gc} {
  set horiz [expr {[$L getDirection] eq "HORIZONTAL"}]
  set tg [$blk findTrackGrid $L]; if {$tg eq "NULL"} { return {} }
  set g [lsort -integer -unique [expr {$horiz ? [$tg getGridY] : [$tg getGridX]}]]
  set hw [expr {[$L getWidth] / 2}]; set sp [$L getSpacing]
  set spans {}
  foreach net [$blk getNets] {
    if {![$net isSpecial]} continue
    set st [$net getSigType]; if {$st ne "POWER" && $st ne "GROUND"} continue
    foreach sw [$net getSWires] { foreach w [$sw getWires] {
      if {[$w isVia] || [$w getTechLayer] ne $L} continue
      set dx [expr {[$w xMax] - [$w xMin]}]; set dy [expr {[$w yMax] - [$w yMin]}]
      if {$horiz} { if {$dx <= $dy} continue; dict set spans "[$w yMin] [$w yMax]" 1 } else { if {$dy <= $dx} continue; dict set spans "[$w xMin] [$w xMax]" 1 }
    } }
  }
  # rows touched by a stripe; count legal tracks there
  set cand {}
  dict for {s _} $spans { lassign $s lo hi
    for {set r [expr {($lo - $hw - $sp) / $gc}]} {$r <= ($hi + $hw + $sp) / $gc} {incr r} { dict lappend cand $r $s } }
  set mint [pgrg::env OT_PG_ROW_GUIDES_MIN_TRACKS 1]
  set bad {}
  dict for {r ss} $cand {
    if {[pgrg::legal_tracks $g [expr {$r * $gc}] [expr {($r + 1) * $gc}] $ss $hw $sp] <= $mint} { dict set bad $r 1 }
  }
  set ::pgrg::touched [dict keys $cand]
  return $bad
}
proc pgrg::run {} {
  if {[pgrg::env OT_PG_ROW_GUIDES 1] eq "0"} { puts "OT_PG_ROW_GUIDES off"; return }
  set blk [ord::get_db_block]; set tech [ord::get_db_tech]
  set gc [expr {int(round([pgrg::env OT_PG_ROW_GUIDES_GCELL_UM 0.57] * [$blk getDbUnitsPerMicron]))}]
  set minlen [pgrg::env OT_PG_ROW_GUIDES_MIN_GCELLS 2]
  foreach ln [pgrg::env OT_PG_ROW_GUIDES_LAYERS M6] {
    set L [$tech findLayer $ln]; if {$L eq "NULL"} continue
    set horiz [expr {[$L getDirection] eq "HORIZONTAL"}]; set lv [$L getRoutingLevel]
    set bad [pgrg::bad_rows $blk $L $gc]
    set touch {}; foreach t $::pgrg::touched { dict set touch $t 1 }
    set moved 0; set len 0; set conn 0; set stuck 0; set nets 0
    foreach net [$blk getNets] {
      if {[$net isSpecial]} continue
      set gs [$net getGuides]; if {![llength $gs]} continue
      set todo {}
      foreach g $gs {
        if {[$g getLayer] ne $L} continue
        set bx [$g getBox]
        set w [expr {$horiz ? [$bx yMax] - [$bx yMin] : [$bx xMax] - [$bx xMin]}]
        set l [expr {$horiz ? [$bx xMax] - [$bx xMin] : [$bx yMax] - [$bx yMin]}]
        if {$w != $gc || $l < $minlen * $gc} continue
        set r [expr {($horiz ? [$bx yMin] : [$bx xMin]) / $gc}]
        if {[dict exists $bad $r]} { lappend todo $g }
      }
      if {![llength $todo]} continue
      incr nets
      foreach g $todo {
        set bx [$g getBox]; set x0 [$bx xMin]; set y0 [$bx yMin]; set x1 [$bx xMax]; set y1 [$bx yMax]
        set r [expr {($horiz ? $y0 : $x0) / $gc}]
        set r2 ""
        # first choice: a row no stripe of this layer touches; else any row that is not BAD
        foreach d {1 -1 2 -2 3 -3} { if {![dict exists $touch [expr {$r + $d}]] && $r + $d >= 0} { set r2 [expr {$r + $d}]; break } }
        if {$r2 eq ""} { foreach d {1 -1 2 -2 3 -3} { if {![dict exists $bad [expr {$r + $d}]] && $r + $d >= 0} { set r2 [expr {$r + $d}]; break } } }
        if {$r2 eq ""} { incr stuck; continue }
        set lo [expr {min($r, $r2) * $gc}]; set hi [expr {(max($r, $r2) + 1) * $gc}]
        # connectors for every other guide of the net on this or an adjacent layer that touches the old box
        foreach o [$net getGuides] {
          if {$o eq $g || [lsearch -exact $todo $o] >= 0} continue
          set ol [$o getLayer]; if {abs([$ol getRoutingLevel] - $lv) > 1} continue
          set ob [$o getBox]
          set ix0 [expr {max($x0, [$ob xMin])}]; set iy0 [expr {max($y0, [$ob yMin])}]
          set ix1 [expr {min($x1, [$ob xMax])}]; set iy1 [expr {min($y1, [$ob yMax])}]
          if {$ix0 >= $ix1 || $iy0 >= $iy1} continue
          if {$horiz} { pgrg::mk $net $ol $o $ix0 $lo $ix1 $hi } else { pgrg::mk $net $ol $o $lo $iy0 $hi $iy1 }
          incr conn
        }
        if {$horiz} { pgrg::mk $net $L $g $x0 [expr {$r2 * $gc}] $x1 [expr {($r2 + 1) * $gc}] } else { pgrg::mk $net $L $g [expr {$r2 * $gc}] $y0 [expr {($r2 + 1) * $gc}] $y1 }
        odb::dbGuide_destroy $g
        incr moved; set len [expr {$len + ($horiz ? $x1 - $x0 : $y1 - $y0)}]
      }
    }
    puts [format "OT_PG_ROW_GUIDES %s: %d bad rows (<= %s legal tracks), moved %d guides on %d nets (%.1f um), %d connectors, %d not movable" \
      $ln [dict size $bad] [pgrg::env OT_PG_ROW_GUIDES_MIN_TRACKS 1] $moved $nets [expr {$len / double([$blk getDbUnitsPerMicron])}] $conn $stuck]
  }
}
if {[info exists ::env(OT_PG_ROW_GUIDES_NO_RUN)]} { return }
if {[catch {pgrg::run} e]} { puts "OT_PG_ROW_GUIDES ERROR (guides stay connected; detail route continues): $e" }
