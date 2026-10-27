# MACRO-EDGE VIA GUARD (opt-in route hook; a stateless toggle: source at PRE_GLOBAL_ROUTE to add, at POST_DETAIL_ROUTE
# to remove; the hold ECO re-applies it around its own GRT/DRT with OT_MEG_MODE=add|remove).
#
# Why (s81su qnq/qbe spx + sp8, 2026-10-13, 12 violations on 4 routes, every one the same shape): under the M5 tile cap
# grt_macro_top_layer.tcl gives GRT the real M5 capacity over SRAM macros (M5 is free over them), but M4 under it is
# macro OBS except the 24 nm pin stubs at the vertical edges.  The GCell that STRADDLES a vertical macro edge holds both
# over-macro M5 tracks and channel M5 tracks; GRT sees one cell with M4/M5 capacity, so track assignment may put an edge
# -pin net or a channel net on an over-macro track of that cell (x 214.908 / 214.956 against the edge at 215.352), and
# the only way off it is an M4 jog through the macro obstruction: "Short inst:<sram> net:<n>" on M4 from the track to
# the OBS end (215.280).  A narrow strip next to the pins (0.024..0.30 um) only moved the bridge to the first free track
# inside it.  The guard therefore takes the top routing layer out of the WHOLE straddling GCell over the macro: depth
# OT_MEG_DEPTH_UM (1.2 um, > 2 GCells of 0.57 um) inward from each edge parallel to the layer's direction, leaving the
# last OT_MEG_PIN_UM (0.024 um, the pin stub) free so an exterior via can still land on the stub.  Deeper GCells are
# entirely over the macro: GRT has zero M4 capacity there and never asks for a via.  Cost: ~25 M5 tracks per macro edge.
# No-op without hard macros.  The obstructions never reach the exported view (removed before 5_2_route.odb is written).
# OUTWARD EXTENSION (opt-in OT_MEG_OUT_UM, default 0 = unchanged; KV r7t-hd2 2026-10-18): the GCell grid is not
# aligned to the macro edge, so the GCell straddling a vertical edge keeps the 1-2 top-layer tracks OUTSIDE the macro
# (qkd_d2d_static_r7t-r7t-9a373179e: guide M5 in GCell x 437.76..438.33 vs SRAM edge 438.264); GRT still routes a net
# up that GCell and DRT, unable to fit it on the outside track, climbs on the first unguarded over-macro track (x 435.756,
# just inside the 2.4 um guard) and jogs on M4 through the macro OBS (Short inst:<sram> + VDD on M4).  OT_MEG_OUT_UM
# (> one GCell, e.g. 1.2) extends each edge guard that far OUTSIDE the macro, so the straddling GCell has no top-layer
# capacity at all and the climb lands in the halo, where an M4 jog is legal.  The macro halo must be wider (5.4 um here).
namespace eval ot_meg {
  proc envd {k d} { expr {[info exists ::env($k)] ? $::env($k) : $d} }
  proc run {} {
    set b [ord::get_db_block]; set t [ord::get_db_tech]; set u [$b getDbUnitsPerMicron]
    set ln [envd OT_MEG_LAYER [envd MAX_ROUTING_LAYER ""]]
    if {$ln eq ""} { error "OT_MACRO_EDGE_GUARD: no layer (set OT_MEG_LAYER or MAX_ROUTING_LAYER)" }
    set l [$t findLayer $ln]; if {$l eq "NULL"} { error "OT_MACRO_EDGE_GUARD: layer $ln not in the tech" }
    set depth [expr {round([envd OT_MEG_DEPTH_UM 1.2] * $u)}]; set pin [expr {round([envd OT_MEG_PIN_UM 0.024] * $u)}]
    set out [expr {round([envd OT_MEG_OUT_UM 0] * $u)}]
    set g [$b getGCellGrid]
    if {$g ne "NULL" && [$g getNumGridPatternsX] > 0} {
      # a grid exists (after GRT / in the ECO): the guard must cover a whole straddling GCell
      lassign [$g getGridPatternX 0] gx0 gn gstep
      if {$gstep >= $depth - $pin} { error "OT_MACRO_EDGE_GUARD: GCell step $gstep dbu >= guard depth $depth dbu: raise OT_MEG_DEPTH_UM" }
    }
    set vert [expr {[$l getDirection] eq "VERTICAL"}]
    set rects {}
    foreach i [$b getInsts] {
      if {![[$i getMaster] isBlock]} continue
      set r [$i getBBox]; set x0 [$r xMin]; set y0 [$r yMin]; set x1 [$r xMax]; set y1 [$r yMax]
      if {$vert} {
        if {$x1 - $x0 <= 2 * $depth} { lappend rects [list $x0 $y0 $x1 $y1]; continue }
        lappend rects [list [expr {$x0 + $pin}] $y0 [expr {$x0 + $depth}] $y1] [list [expr {$x1 - $depth}] $y0 [expr {$x1 - $pin}] $y1]
        if {$out > 0} { lappend rects [list [expr {$x0 - $out}] $y0 $x0 $y1] [list $x1 $y0 [expr {$x1 + $out}] $y1] }
      } else {
        if {$y1 - $y0 <= 2 * $depth} { lappend rects [list $x0 $y0 $x1 $y1]; continue }
        lappend rects [list $x0 [expr {$y0 + $pin}] $x1 [expr {$y0 + $depth}]] [list $x0 [expr {$y1 - $depth}] $x1 [expr {$y1 - $pin}]]
        if {$out > 0} { lappend rects [list $x0 [expr {$y0 - $out}] $x1 $y0] [list $x0 $y1 $x1 [expr {$y1 + $out}]] }
      }
    }
    if {![llength $rects]} { puts "OT_MACRO_EDGE_GUARD: skipped (no hard macros)"; return }
    set mine {}
    foreach o [$b getObstructions] {
      set bx [$o getBBox]
      if {[[$bx getTechLayer] getName] ne $ln} continue
      if {[lsearch -exact $rects [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]] >= 0} { lappend mine $o }
    }
    set mode [envd OT_MEG_MODE toggle]
    if {$mode eq "toggle"} { set mode [expr {[llength $mine] ? "remove" : "add"}] }
    if {$mode eq "add"} {
      if {[llength $mine]} { error "OT_MACRO_EDGE_GUARD: add requested but [llength $mine] guards already exist" }
      foreach r $rects { odb::dbObstruction_create $b $l {*}$r }
      puts "OT_MACRO_EDGE_GUARD: created [llength $rects] on $ln (depth [expr {double($depth) / $u}] um, pin stub [expr {double($pin) / $u}] um free, outside [expr {double($out) / $u}] um)"
    } elseif {$mode eq "remove"} {
      if {[llength $mine] != [llength $rects]} { error "OT_MACRO_EDGE_GUARD: expected [llength $rects] guards on $ln, found [llength $mine]" }
      foreach o $mine { odb::dbObstruction_destroy $o }
      puts "OT_MACRO_EDGE_GUARD: removed [llength $mine] on $ln"
    } else { error "OT_MACRO_EDGE_GUARD: OT_MEG_MODE must be add, remove or toggle" }
  }
}
ot_meg::run
