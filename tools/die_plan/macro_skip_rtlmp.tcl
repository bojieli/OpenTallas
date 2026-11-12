# KW-FIX-45 11-12 (COORD ruling, PHY MPL-0006): in a hard-wrapper type every macro is placed and FIXED by the plan
# (macro_place.tcl: place_macro -exact at the plan site), so ORFS' rtl_macro_placer has nothing to decide, and with the
# platform 10 um halo it only fails ("MPL-0006 Found macro that does not fit in the core") when the macro reaches a core side
# (the PHY macro spans the full core width).  Sourced as PRE_MACRO_PLACE_TCL, before macro_place_util.tcl: the placer command
# is replaced by a no-op that marks every macro FIRM (what MPL-0062 "Found fixed macro" assumes), keeping the plan
# placement.  Only generated for kits whose type is a hard wrapper; every other kit still runs rtl_macro_placer.
proc ::rtl_macro_placer {args} {
  set n 0
  if {[info commands ord::get_db_block] ne ""} {
    foreach i [[ord::get_db_block] getInsts] {
      if {[[$i getMaster] isBlock]} { $i setPlacementStatus FIRM; incr n }
    }
  }
  puts "OT_RTLMP_SKIP: all $n macro(s) are plan-fixed; rtl_macro_placer skipped (args: $args)"
}
