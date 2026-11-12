# CLOCK-PIN LANDING GUARD (HBM-CORE-WBQ-1 2026-11-12; opt-in route hook, a stateless add/remove: source at
# PRE_GLOBAL_ROUTE with OT_CPL_MODE=add, at POST_DETAIL_ROUTE with OT_CPL_MODE=remove).
#
# Why (OBS-SYNC-1 02:10 11-12, ot_wbq_root_g0): an INTERIOR clock entry (M5 pin 0.048 x 0.48 at plan point, METHODOLOGY
# 12.8a) sits in the middle of the core's routing.  The core's own M6 signal routing filled every M6 track over the pin
# span (S7 signed DB: 8 tracks y 25.68..26.16 at x 108.0 / 108.19, hbm_clk + fifo_clk both boxed in by 25+ M6 nets that
# run x 61..195), so the parent router has no M6 landing for VIA56 on the pin: DRT-0073 "No access point" with any
# view, because the detail view carries the real metal.  An abstract cannot fix that.
# This hook keeps the M6 tracks over each interior clock pin free of core routing: during GRT and DRT an M6 routing
# obstruction covers the pin span widened by OT_CPL_PAD_X_UM each side in x and OT_CPL_PAD_Y_UM in y; the core's own
# clock net reaches the pin on M4/M5 (it never needs that M6 window).  The obstruction is a route exclusion only: it is
# removed after DRT, so the exported/routed DB carries no metal there and the parent lands VIA56 + an M6 stub.
# END GUARD (HBM-CORES-C 11-12, ot_wbq_root_g0 ffc build: 6 DRC "Rect Only" on M5 at the pin tops of fifo_clk / hbm_clk): the
# core's own clock net reaches the pin from M4 with a V4 + M5 enclosure.  DRT put that via on the topmost M4 track of the pin
# (y 26.136), so its M5 enclosure overshoots the pin end by 0.024 um and leaves a sub-pitch M5 sliver.  A second exclusion on
# OT_CPL_END_LAYER (M4) over each pin end, OT_CPL_END_CLEAR_UM (0.06) into the pin and OT_CPL_END_PAD_UM beyond it, widened
# OT_CPL_END_X_UM each side in x, keeps the landing via inside the pin rect.  Removed after DRT like the M6 guard.
# Pins on a face (within OT_CPL_FACE_UM of the core edge) and non-M5 pins are skipped.  No-op without such pins.
namespace eval ot_cpl {
  proc envd {k d} { expr {[info exists ::env($k)] ? $::env($k) : $d} }
  proc run {} {
    set b [ord::get_db_block]; set t [ord::get_db_tech]; set u [$b getDbUnitsPerMicron]
    set l [$t findLayer [envd OT_CPL_LAYER M6]]
    if {$l eq "NULL"} { error "OT_CLOCK_PIN_LANDING_GUARD: layer not in the tech" }
    set mode [envd OT_CPL_MODE ""]
    if {$mode ni {add remove}} { error "OT_CLOCK_PIN_LANDING_GUARD: OT_CPL_MODE must be add or remove" }
    set ports [envd OT_CPL_PORTS ""]
    if {$ports eq ""} { error "OT_CLOCK_PIN_LANDING_GUARD: OT_CPL_PORTS empty" }
    set px [expr {round([envd OT_CPL_PAD_X_UM 1.0] * $u)}]; set py [expr {round([envd OT_CPL_PAD_Y_UM 0.064] * $u)}]
    set fc [expr {round([envd OT_CPL_FACE_UM 1.0] * $u)}]
    set die [$b getDieArea]
    set rects {}
    set erects {}
    set el [$t findLayer [envd OT_CPL_END_LAYER M4]]
    if {$el eq "NULL"} { error "OT_CLOCK_PIN_LANDING_GUARD: end layer not in the tech" }
    set ec [expr {round([envd OT_CPL_END_CLEAR_UM 0.06] * $u)}]; set ep [expr {round([envd OT_CPL_END_PAD_UM 0.064] * $u)}]
    set ex [expr {round([envd OT_CPL_END_X_UM 0.1] * $u)}]
    foreach bt [$b getBTerms] {
      if {[lsearch -exact $ports [$bt getName]] < 0} continue
      foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
        if {[[$bx getTechLayer] getName] ne "M5"} continue
        set x0 [$bx xMin]; set y0 [$bx yMin]; set x1 [$bx xMax]; set y1 [$bx yMax]
        if {$x0 - [$die xMin] < $fc || [$die xMax] - $x1 < $fc || $y0 - [$die yMin] < $fc || [$die yMax] - $y1 < $fc} continue
        lappend rects [list [expr {$x0 - $px}] [expr {$y0 - $py}] [expr {$x1 + $px}] [expr {$y1 + $py}]]
        if {$ec > 0} {
          lappend erects [list [expr {$x0 - $ex}] [expr {$y1 - $ec}] [expr {$x1 + $ex}] [expr {$y1 + $ep}]]
          lappend erects [list [expr {$x0 - $ex}] [expr {$y0 - $ep}] [expr {$x1 + $ex}] [expr {$y0 + $ec}]]
        }
      } }
    }
    set mine {}
    foreach o [$b getObstructions] {
      set bx [$o getBBox]
      if {[[$bx getTechLayer] getName] ne [$l getName]} continue
      if {[lsearch -exact $rects [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]] >= 0} { lappend mine $o }
    }
    set emine {}
    foreach o [$b getObstructions] {
      set bx [$o getBBox]
      if {[[$bx getTechLayer] getName] ne [$el getName]} continue
      if {[lsearch -exact $erects [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]] >= 0} { lappend emine $o }
    }
    if {$mode eq "add"} {
      if {[llength $mine] || [llength $emine]} { error "OT_CLOCK_PIN_LANDING_GUARD: add requested but [expr {[llength $mine] + [llength $emine]}] guards already exist" }
      foreach r $rects { set o [odb::dbObstruction_create $b $l {*}$r]; $o setMinSpacing 0 }
      foreach r $erects { set o [odb::dbObstruction_create $b $el {*}$r]; $o setMinSpacing 0 }
      puts "OT_CLOCK_PIN_LANDING_GUARD: created [llength $rects] on [$l getName] + [llength $erects] end guards on [$el getName] for $ports"
    } else {
      if {[llength $mine] != [llength $rects] || [llength $emine] != [llength $erects]} { error "OT_CLOCK_PIN_LANDING_GUARD: expected [llength $rects]+[llength $erects] guards, found [llength $mine]+[llength $emine]" }
      foreach o $mine { odb::dbObstruction_destroy $o }
      foreach o $emine { odb::dbObstruction_destroy $o }
      puts "OT_CLOCK_PIN_LANDING_GUARD: removed [llength $mine] on [$l getName] + [llength $emine] end guards on [$el getName]"
    }
  }
}
ot_cpl::run
