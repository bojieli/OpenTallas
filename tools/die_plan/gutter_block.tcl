# GENERATED copy of tools/die_plan/gutter_block.tcl (sourced at the end of face_flops.tcl, PRE_GLOBAL_PLACE, after
# relay_mid.tcl).  NARROW-GUTTER class (S81-TYPES-5 11-07, COORD 15:3x t56 smell + COLH10 e10 channels): GPL put
# high-fanout drivers (vp_cf native_memory words, fanout 5 over 925 um of LN macros; vp_rr rst_n fanout 53) and relay
# clusters into the 6-40 um gutters between macro columns, because a gutter is the centroid of the macro pins on both
# sides.  The gutter then has no room for the wires that must pass it.  Opt-in OT_GUTTER_BLOCK_UM=<G> (default off = no
# file effect): every gap narrower than G between two facing macros (overlapping span on the other axis) gets a hard
# placement blockage over the gap, so soft logic lands on the open side of the macro row/column.  Routing is unchanged
# (placement blockage only).  FIRM / LOCKED cells already in a gutter (landing rings, plan stations) are not moved; a
# released FIRM cell is legalised out of the gutter by DPL.  Gaps along the core edge are left alone (pin access).
# GUTTER-LAND-CARVE 11-24 (KV-OWN-RSTREACH, FAIL-CLASS f5fa4d600f "clock-landing band too small or blocked", 81 h / 13 owners):
# the landing windows (landing_placement.tcl cland_groups) are plan sites drawn before this file exists.  On kv3_pc
# cl254f2e73 / cl5a95b461 (A5t5, D29) the reader-start windows i_embgw_est_5 and i_vport_Q_N_vqN_5 lie wholly inside the
# 34.56 um kvpc|kvpc_f gutter; OT_GUTTER_BLOCK_UM = 35 made the gutter one HARD blockage, landing_placement.tcl occupies
# hard blockages, and the band (need 1.2 um2 of 18.7) and even its x32 grow (all gutter + macro) had no site: 8 of 8 band
# fails in 4 kits, 0 other causes.  Every landing window is cut out of the gutter rects here (gb_carve = pure rect minus
# rects, the gr_carve / mhc_carve law), so the planned landing cells keep their sites and soft logic still sees the rest
# of the gutter blocked.  ot_gutter_block.txt lists the carved rects, so gutter_release.tcl removes / re-cuts exactly these.
# OT_GUTTER_LAND_CARVE=0 gives the old one-rect-per-gutter behaviour.  No window in a gutter: byte-identical blockages.
proc gb_carve {rect cells} {
  lassign $rect x0 y0 x1 y1
  set hit {}
  foreach c $cells {
    lassign $c a b d e
    if {$d > $x0 && $a < $x1 && $e > $y0 && $b < $y1} { lappend hit [list [expr {max($a, $x0)}] [expr {max($b, $y0)}] [expr {min($d, $x1)}] [expr {min($e, $y1)}]] }
  }
  if {![llength $hit]} { return [list $rect] }
  set ys [list $y0 $y1]
  foreach h $hit { lappend ys [lindex $h 1] [lindex $h 3] }
  set ys [lsort -integer -unique $ys]
  set out {}; set prev {}; set py0 ""
  for {set i 0} {$i < [llength $ys] - 1} {incr i} {
    set ya [lindex $ys $i]; set yb [lindex $ys [expr {$i + 1}]]
    set iv {}
    foreach h $hit { lassign $h a b d e; if {$e > $ya && $b < $yb} { lappend iv [list $a $d] } }
    set segs {}; set x $x0
    foreach v [lsort -integer -index 0 $iv] { lassign $v a d; if {$a > $x} { lappend segs [list $x $a] }; if {$d > $x} { set x $d } }
    if {$x < $x1} { lappend segs [list $x $x1] }
    if {$py0 ne "" && $segs eq $prev} continue
    if {$py0 ne ""} { foreach s $prev { lappend out [list [lindex $s 0] $py0 [lindex $s 1] $ya] } }
    set prev $segs; set py0 $ya
  }
  foreach s $prev { lappend out [list [lindex $s 0] $py0 [lindex $s 1] $y1] }
  return $out
}
# Landing windows of a landing_placement.tcl text, in DBU: {x0 y0 x1 y1} per cland_groups entry (pure).
proc gb_land_windows {txt dbu} {
  set i [string first "set cland_groups \{\n" $txt]
  if {$i < 0} { return {} }
  set j [string first "\n\}\n" $txt $i]
  if {$j < 0} { return {} }
  set out {}
  foreach spec [string range $txt [expr {$i + 18}] $j] {
    lassign $spec name rect tag
    if {[llength $rect] != 4} continue
    lassign $rect a b c d
    lappend out [list [expr {int(floor($a * $dbu))}] [expr {int(floor($b * $dbu))}] [expr {int(ceil($c * $dbu))}] [expr {int(ceil($d * $dbu))}]]
  }
  return $out
}
uplevel #0 {
if {[info exists ::env(OT_GUTTER_BLOCK_UM)] && $::env(OT_GUTTER_BLOCK_UM) > 0} {
  set gb_blk [ord::get_db_block]
  set gb_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set gb_g [expr {int($::env(OT_GUTTER_BLOCK_UM) * $gb_dbu)}]
  set gb_min [expr {int(0.27 * $gb_dbu)}]
  # S81-TYPES-7-COLH 11-08: OT_GUTTER_BLOCK_MIN_SPAN_UM (opt-in) = only gaps facing over at least this span
  if {[info exists ::env(OT_GUTTER_BLOCK_MIN_SPAN_UM)] && $::env(OT_GUTTER_BLOCK_MIN_SPAN_UM) > 0} {
    set gb_min [expr {max($gb_min, int($::env(OT_GUTTER_BLOCK_MIN_SPAN_UM) * $gb_dbu))}]
  }
  set gb_m {}
  foreach i [$gb_blk getInsts] {
    if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend gb_m [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] }
  }
  set gb_n 0; set gb_area 0.0
  set gb_rects {}
  set n [llength $gb_m]
  for {set a 0} {$a < $n} {incr a} {
    lassign [lindex $gb_m $a] ax0 ay0 ax1 ay1
    for {set b 0} {$b < $n} {incr b} {
      if {$a == $b} continue
      lassign [lindex $gb_m $b] bx0 by0 bx1 by1
      # vertical gutter: b right of a, y spans overlap
      set gx [expr {$bx0 - $ax1}]
      set oy0 [expr {max($ay0, $by0)}]; set oy1 [expr {min($ay1, $by1)}]
      if {$gx > 0 && $gx < $gb_g && $oy1 - $oy0 > $gb_min} {
        set clear 1
        foreach m $gb_m { lassign $m mx0 my0 mx1 my1
          if {$mx0 < $bx0 && $mx1 > $ax1 && $my0 < $oy1 && $my1 > $oy0} { set clear 0; break } }
        if {$clear} { lappend gb_rects [list $ax1 $oy0 $bx0 $oy1] }
      }
      # horizontal gutter: b above a, x spans overlap
      set gy [expr {$by0 - $ay1}]
      set ox0 [expr {max($ax0, $bx0)}]; set ox1 [expr {min($ax1, $bx1)}]
      if {$gy > 0 && $gy < $gb_g && $ox1 - $ox0 > $gb_min} {
        set clear 1
        foreach m $gb_m { lassign $m mx0 my0 mx1 my1
          if {$my0 < $by0 && $my1 > $ay1 && $mx0 < $ox1 && $mx1 > $ox0} { set clear 0; break } }
        if {$clear} { lappend gb_rects [list $ox0 $ay1 $ox1 $by0] }
      }
    }
  }
  if {!([info exists ::env(OT_GUTTER_LAND_CARVE)] && $::env(OT_GUTTER_LAND_CARVE) eq "0") && [file exists /work/landing_placement.tcl] && [llength $gb_rects]} {
    set gb_fh [open /work/landing_placement.tcl r]; set gb_lw [gb_land_windows [read $gb_fh] $gb_dbu]; close $gb_fh
    set gb_cut {}; set gb_nw 0
    foreach r $gb_rects {
      lassign $r x0 y0 x1 y1
      set hw {}
      foreach w $gb_lw { lassign $w a b c d; if {$c > $x0 && $a < $x1 && $d > $y0 && $b < $y1} { lappend hw $w } }
      incr gb_nw [llength $hw]
      foreach q [gb_carve $r $hw] { lassign $q a b c d; if {$c > $a && $d > $b} { lappend gb_cut $q } }
    }
    if {$gb_nw} { puts "OT_GUTTER_BLOCK GUTTER-LAND-CARVE: $gb_nw landing window(s) cut out of [llength $gb_rects] gutter(s) -> [llength $gb_cut] blockage rects" }
    set gb_rects $gb_cut
  }
  set gb_log [open $::env(RESULTS_DIR)/ot_gutter_block.txt w]
  foreach r $gb_rects {
    lassign $r x0 y0 x1 y1
    odb::dbBlockage_create $gb_blk $x0 $y0 $x1 $y1
    incr gb_n
    set gb_area [expr {$gb_area + ($x1 - $x0) * ($y1 - $y0) / double($gb_dbu * $gb_dbu)}]
    puts $gb_log "[expr {$x0 / double($gb_dbu)}]\t[expr {$y0 / double($gb_dbu)}]\t[expr {$x1 / double($gb_dbu)}]\t[expr {$y1 / double($gb_dbu)}]"
  }
  close $gb_log
  puts "OT_GUTTER_BLOCK $gb_n gutter placement blockages (gap < $::env(OT_GUTTER_BLOCK_UM) um between facing macros), [format %.1f $gb_area] um2"
}
}
