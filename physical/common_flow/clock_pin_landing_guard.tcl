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
    foreach bt [$b getBTerms] {
      if {[lsearch -exact $ports [$bt getName]] < 0} continue
      foreach bp [$bt getBPins] { foreach bx [$bp getBoxes] {
        if {[[$bx getTechLayer] getName] ne "M5"} continue
        set x0 [$bx xMin]; set y0 [$bx yMin]; set x1 [$bx xMax]; set y1 [$bx yMax]
        if {$x0 - [$die xMin] < $fc || [$die xMax] - $x1 < $fc || $y0 - [$die yMin] < $fc || [$die yMax] - $y1 < $fc} continue
        lappend rects [list [expr {$x0 - $px}] [expr {$y0 - $py}] [expr {$x1 + $px}] [expr {$y1 + $py}]]
      } }
    }
    set mine {}
    foreach o [$b getObstructions] {
      set bx [$o getBBox]
      if {[[$bx getTechLayer] getName] ne [$l getName]} continue
      if {[lsearch -exact $rects [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax]]] >= 0} { lappend mine $o }
    }
    if {$mode eq "add"} {
      if {[llength $mine]} { error "OT_CLOCK_PIN_LANDING_GUARD: add requested but [llength $mine] guards already exist" }
      foreach r $rects { set o [odb::dbObstruction_create $b $l {*}$r]; $o setMinSpacing 0 }
      puts "OT_CLOCK_PIN_LANDING_GUARD: created [llength $rects] on [$l getName] for $ports"
    } else {
      if {[llength $mine] != [llength $rects]} { error "OT_CLOCK_PIN_LANDING_GUARD: expected [llength $rects] guards, found [llength $mine]" }
      foreach o $mine { odb::dbObstruction_destroy $o }
      puts "OT_CLOCK_PIN_LANDING_GUARD: removed [llength $mine] on [$l getName]"
    }
  }
}
ot_cpl::run
