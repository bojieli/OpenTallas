# QC-SU-SRAMHALO (2026-10-27, COORD 05:4x): PRE_GLOBAL_ROUTE M2-M5 ROUTING keep-off at every hard-macro corner where a
# pin column meets the macro top/bottom edge.  Shared form of the QC-SU-BTAB-R5 hook (GEOM-REVIEW-7 PASS, btab r5 DRT 0
# at it 11; r4 residue sat at the NE SRAM corner, prog L2 residue (55 markers) at the NE corner of SRAM band 2): with the
# std-cell exclusion strips of gen_core_kit_qc.py (sram_pincol_halo.json) it is ONE structural fix for both.
# Per macro edge that carries signal pins (W/E faces): an L-shaped box pair per corner
#   (a) outside the face: OT_PCH_CKO_X (1.08) wide, from OT_PCH_CKO_IN (0.30) inside the macro edge to OT_PCH_CKO_Y (2.16)
#       into the gap, layers M2-M5;
#   (b) over the macro corner: same y span, OT_PCH_CKO_X inside the face, M5 only (M2-M4 are macro OBS already).
# Nets crossing the gap therefore enter it >= OT_PCH_CKO_Y from the macro edge, nothing turns around the corner.
# Boxes overlapping a special-net (PDN) shape on their layer are skipped and reported.  No globals (may be sourced in a proc).
#
# KW-FIX-43 (2026-11-10, DIE-QC-97, su_lane l0t/l5s 2 M4 Shorts at g_native_bank[1].u_tlm E face): the boxes were
# sub-gcell.  GRT (gcell 0.570 um on these kits) sees them only as partial capacity, so the corner gcell row that holds
# the box inner edge (e.g. box 165.42 inside row 165.30-165.87, macro top 165.72) kept 2-3 free M4/M2 tracks east of the
# face that no legal M3/M5 path reaches (M3 above the macro is cut off by the box, below it by the macro OBS).  GRT put
# 2 nets through that pocket; DRT left the guide, ran M5 over the macro, dropped V45 1.6 um inside the face and crossed
# the M4 OBS (5_route_drc.rpt, both kits).  Snap (OT_PCH_CKO_SNAP=1, default): every box edge that is not the macro
# face moves OUTWARD to the GRT gcell grid (OT_PCH_CKO_GCELL um, default = the odb gcell grid if present, else 0.570),
# and the inner y edge also covers the gcell boundary by one M4 pitch (OT_PCH_CKO_COVER 0.048), so the corner gcells
# carry zero GRT capacity on the blocked layers and no guide can enter a pocket.  Guards, each falling back to the
# original (unsnapped) box for that corner and reported: the inner edge would come closer than OT_PCH_CKO_PINCLR (0.096)
# to a signal pin of that face; the extension would touch a std cell; the snapped box hits PDN where the original does
# not.  OT_PCH_CKO_SNAP=0 = the 10-27 boxes exactly.
proc ot_pch_env {k d} { expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d} }
proc ot_pch_hit {pg lay xa ya xb yb} {
  foreach p $pg { lassign $p l a c d e; if {$l eq $lay && $a < $xb && $d > $xa && $c < $yb && $e > $ya} { return 1 } }
  return 0
}
proc ot_pch_cell_hit {cells xa ya xb yb} {
  foreach r $cells { lassign $r a c d e; if {$a < $xb && $d > $xa && $c < $yb && $e > $ya} { return 1 } }
  return 0
}
proc ot_pch_keepoff {} {
  set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]; set t [ord::get_db_tech]
  set X [expr {round([ot_pch_env OT_PCH_CKO_X 1.08] * $u)}]; set Y [expr {round([ot_pch_env OT_PCH_CKO_Y 2.16] * $u)}]
  set I [expr {round([ot_pch_env OT_PCH_CKO_IN 0.30] * $u)}]
  set snap [ot_pch_env OT_PCH_CKO_SNAP 1]
  set C [expr {round([ot_pch_env OT_PCH_CKO_COVER 0.048] * $u)}]
  set PC [expr {round([ot_pch_env OT_PCH_CKO_PINCLR 0.096] * $u)}]
  set G 0; set gsrc off
  if {$snap ne "0"} {
    set gv [ot_pch_env OT_PCH_CKO_GCELL ""]
    if {$gv ne ""} { set G [expr {round($gv * $u)}]; set gsrc env } else {
      set gg [$b getGCellGrid]
      if {$gg ne "NULL" && $gg ne ""} {
        set gx [$gg getGridX]
        if {[llength $gx] > 1} { set G [expr {[lindex $gx 1] - [lindex $gx 0]}]; set gsrc odb }
      }
      if {$G <= 0} { set G [expr {round(0.570 * $u)}]; set gsrc default }
    }
  }
  set pg {}
  foreach n [$b getNets] {
    if {![$n isSpecial]} continue
    foreach sw [$n getSWires] { foreach w [$sw getWires] { if {![$w isVia]} { lappend pg [list [[$w getTechLayer] getName] [$w xMin] [$w yMin] [$w xMax] [$w yMax]] } } }
  }
  # std cells within 4 gcells of any macro (snap guard)
  set mac {}
  foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { set bb [$i getBBox]; lappend mac [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] } }
  set cells {}
  if {$G > 0} {
    set R [expr {4 * $G + $X + $Y}]
    foreach i [$b getInsts] {
      set mt [[$i getMaster] getType]
      if {[[$i getMaster] isBlock] || $mt eq "CORE_WELLTAP" || [string match "ENDCAP*" $mt]} continue
      set bb [$i getBBox]
      foreach m $mac {
        lassign $m a c d e
        if {[$bb xMin] < $d + $R && [$bb xMax] > $a - $R && [$bb yMin] < $e + $R && [$bb yMax] > $c - $R} {
          lappend cells [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]; break
        }
      }
    }
  }
  set n 0; set s 0; set ns 0; set nf 0; set f [open $::env(RESULTS_DIR)/sram_pincol_keepoff.txt w]
  puts $f [format "SNAP %s gcell %.3f (%s) cover %.3f pinclr %.3f" $snap [expr {$G / double($u)}] $gsrc [expr {$C / double($u)}] [expr {$PC / double($u)}]]
  foreach i [$b getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set bb [$i getBBox]; set X0 [$bb xMin]; set X1 [$bb xMax]; set Y0 [$bb yMin]; set Y1 [$bb yMax]
    # faces that carry signal pins (instance frame) and their pin y extent per face
    set faces {}; array unset pmin; array unset pmax
    foreach it [$i getITerms] {
      if {[$it getNet] eq "NULL" || [[$it getNet] getSigType] in {POWER GROUND}} continue
      set r [$it getBBox]
      if {[$r xMin] - $X0 < $u / 10} { set fc W } elseif {$X1 - [$r xMax] < $u / 10} { set fc E } else { continue }
      lappend faces $fc
      if {![info exists pmin($fc)] || [$r yMin] < $pmin($fc)} { set pmin($fc) [$r yMin] }
      if {![info exists pmax($fc)] || [$r yMax] > $pmax($fc)} { set pmax($fc) [$r yMax] }
    }
    foreach side [lsort -unique $faces] {
      foreach end {S N} {
        set ya [expr {$end eq "N" ? $Y1 - $I : $Y0 - $Y}]; set yb [expr {$end eq "N" ? $Y1 + $Y : $Y0 + $I}]
        set out [expr {$side eq "E" ? [list $X1 [expr {$X1 + $X}]] : [list [expr {$X0 - $X}] $X0]}]
        set ins [expr {$side eq "E" ? [list [expr {$X1 - $X}] $X1] : [list $X0 [expr {$X0 + $X}]]}]
        set o_ya $ya; set o_yb $yb; set o_out $out; set o_ins $ins; set why ""
        if {$G > 0} {
          # outward snap; inner y edge (inside the macro y span) also covers the gcell boundary by C
          if {$end eq "N"} {
            set s_ya [expr {int(floor($ya / double($G))) * $G - $C}]; set s_yb [expr {int(ceil($yb / double($G))) * $G}]
            if {[info exists pmax($side)] && $s_ya < $pmax($side) + $PC} { set why "pinclr" }
          } else {
            set s_ya [expr {int(floor($ya / double($G))) * $G}]; set s_yb [expr {int(ceil($yb / double($G))) * $G + $C}]
            if {[info exists pmin($side)] && $s_yb > $pmin($side) - $PC} { set why "pinclr" }
          }
          if {$side eq "E"} {
            set s_out [list $X1 [expr {int(ceil(($X1 + $X) / double($G))) * $G}]]
          } else {
            set s_out [list [expr {int(floor(($X0 - $X) / double($G))) * $G}] $X0]
          }
          # the M5 box over the macro keeps its x span (macro M5 PG stripes sit just inside it); only its y edges snap
          set s_ins $ins
          lassign $s_out sxa sxb; lassign $o_out oxa oxb
          if {$why eq "" && [ot_pch_cell_hit $cells $sxa $s_ya $sxb $s_yb] && ![ot_pch_cell_hit $cells $oxa $o_ya $oxb $o_yb]} {
            set why "stdcell"
          }
          if {$why eq ""} {
            foreach lay {M2 M3 M4 M5} {
              if {[ot_pch_hit $pg $lay $sxa $s_ya $sxb $s_yb] && ![ot_pch_hit $pg $lay $oxa $o_ya $oxb $o_yb]} { set why "pdn"; break }
            }
            lassign $s_ins sxa sxb; lassign $o_ins oxa oxb
            if {$why eq "" && [ot_pch_hit $pg M5 $sxa $s_ya $sxb $s_yb] && ![ot_pch_hit $pg M5 $oxa $o_ya $oxb $o_yb]} { set why "pdn" }
          }
          if {$why eq ""} { set ya $s_ya; set yb $s_yb; set out $s_out; set ins $s_ins; incr ns } else {
            incr nf; puts $f "SNAP_FALLBACK [$i getName] $end$side $why"
          }
        }
        foreach lay {M2 M3 M4 M5} {
          foreach part {out ins} {
            if {$part eq "ins" && $lay ne "M5"} continue
            lassign [set $part] xa xb
            if {[ot_pch_hit $pg $lay $xa $ya $xb $yb]} { incr s; puts $f "SKIP_PG [$i getName] $side$end $lay $part"; continue }
            odb::dbObstruction_create $b [$t findLayer $lay] $xa $ya $xb $yb; incr n
            puts $f [format "KEEPOFF %s %s%s %s %s %.3f %.3f %.3f %.3f" [$i getName] $end $side $lay $part \
              [expr {$xa / double($u)}] [expr {$ya / double($u)}] [expr {$xb / double($u)}] [expr {$yb / double($u)}]]
          }
        }
      }
    }
  }
  close $f
  puts "SRAM_PINCOL_KEEPOFF $n routing obstructions (M2-M5) at macro pin-face corners, $s skipped for PDN overlap,\
 gcell snap $snap ([expr {$G / double($u)}] um $gsrc): $ns corners snapped, $nf kept unsnapped"
}
ot_pch_keepoff
