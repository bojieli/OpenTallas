# q13-coll 2026-10-13: macro pin-edge access guard (PRE_GLOBAL_ROUTE create / POST_DETAIL_ROUTE remove).
# Root cause it fixes (coll_col_tile ct1..ct5, qfd_slab_pg_col c1..c4: every residual DRC is M4 at a macro E edge,
# bbox starting exactly at the M4 OBS edge = macro xMax - 0.072): the memory macros carry their pins as 24 nm M4
# stubs on the W/E edge, the M4 OBS stops 72 nm inside, and M5 is free over the whole macro. GRT (M5 capacity over
# macros, grt_macro_top_layer.tcl) brings nets over the macro on M5 and detailed routing drops a VIA45 on an
# interior M5 track next to the pin: its M4 landing/stub then sits 13-53 nm from the wide M4 OBS (Metal Spacing /
# EOL) or crosses it (Short). The pins are meant to be reached planar on M4 from the channel side.
# Fix: a temporary M5 route keepout over the macro's pin-edge band (default 2.16 um = 4 GRT gcells, so GRT sees no
# M5 capacity there either, plus 12 nm past the edge) so every pin is entered on its own M4 track from the channel.
# The keepout ADDS a restriction and is removed after detailed routing: the exported view carries only real metal.
#   OT_MEG_MASTER  glob list of macro masters (required)      OT_MEG_EXPECT  number of guarded macros (required)
#   OT_MEG_BAND    band width in um (default 2.16; "full" = whole macro)   OT_MEG_EDGES  EW (default) | E | W
set ot_meg_stage ""
for {set ot_meg_f [info frame]} {$ot_meg_f > 0} {incr ot_meg_f -1} {
  set ot_meg_d [info frame $ot_meg_f]
  if {![dict exists $ot_meg_d file]} continue
  set ot_meg_t [file tail [dict get $ot_meg_d file]]
  if {[string match *pre_grt.tcl $ot_meg_t]} { set ot_meg_stage create; break }
  if {[string match *post_drt.tcl $ot_meg_t]} { set ot_meg_stage remove; break }
  if {[string match *pre_cts.tcl $ot_meg_t]} { set ot_meg_stage skip; break }
}
if {$ot_meg_stage eq ""} { puts "OT_MEG skipped: no *pre_cts/*pre_grt/*post_drt hook file on the Tcl stack"; set ot_meg_stage skip }
if {$ot_meg_stage ne "skip"} {
  set ot_meg_b [ord::get_db_block]
  set ot_meg_u [$ot_meg_b getDbUnitsPerMicron]
  set ot_meg_l [[ord::get_db_tech] findLayer [expr {[info exists ::env(OT_MEG_LAYER)] ? $::env(OT_MEG_LAYER) : "M5"}]]
  set ot_meg_band [expr {[info exists ::env(OT_MEG_BAND)] ? $::env(OT_MEG_BAND) : 2.16}]
  set ot_meg_edges [expr {[info exists ::env(OT_MEG_EDGES)] ? $::env(OT_MEG_EDGES) : "EW"}]
  set ot_meg_out [expr {round(0.012 * $ot_meg_u)}]
  set ot_meg_rects {}
  set ot_meg_n 0
  foreach ot_meg_i [$ot_meg_b getInsts] {
    set ot_meg_m [[$ot_meg_i getMaster] getName]
    set ot_meg_hit 0
    foreach ot_meg_p $::env(OT_MEG_MASTER) { if {[string match $ot_meg_p $ot_meg_m]} { set ot_meg_hit 1 } }
    if {!$ot_meg_hit} continue
    incr ot_meg_n
    set ot_meg_r [$ot_meg_i getBBox]
    set x0 [$ot_meg_r xMin]; set x1 [$ot_meg_r xMax]; set y0 [$ot_meg_r yMin]; set y1 [$ot_meg_r yMax]
    if {$ot_meg_band eq "full"} {
      lappend ot_meg_rects [list [expr {$x0 - $ot_meg_out}] $y0 [expr {$x1 + $ot_meg_out}] $y1]
    } else {
      set w [expr {round($ot_meg_band * $ot_meg_u)}]
      if {[string first E $ot_meg_edges] >= 0} { lappend ot_meg_rects [list [expr {$x1 - $w}] $y0 [expr {$x1 + $ot_meg_out}] $y1] }
      if {[string first W $ot_meg_edges] >= 0} { lappend ot_meg_rects [list [expr {$x0 - $ot_meg_out}] $y0 [expr {$x0 + $w}] $y1] }
    }
  }
  if {$ot_meg_n != $::env(OT_MEG_EXPECT)} { error "OT_MEG: expected $::env(OT_MEG_EXPECT) guarded macros, found $ot_meg_n" }
  set ot_meg_c 0
  if {$ot_meg_stage eq "create"} {
    foreach r $ot_meg_rects { odb::dbObstruction_create $ot_meg_b $ot_meg_l {*}$r; incr ot_meg_c }
  } else {
    foreach o [$ot_meg_b getObstructions] {
      set r [$o getBBox]
      if {[[$r getTechLayer] getName] ne [$ot_meg_l getName]} continue
      if {[lsearch -exact $ot_meg_rects [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]] >= 0} { odb::dbObstruction_destroy $o; incr ot_meg_c }
    }
  }
  if {$ot_meg_c != [llength $ot_meg_rects]} { error "OT_MEG: $ot_meg_stage $ot_meg_c of [llength $ot_meg_rects] guards" }
  puts "OT_MEG $ot_meg_stage $ot_meg_c guards on [$ot_meg_l getName] over $ot_meg_n macros (band $ot_meg_band um, edges $ot_meg_edges)"
}
