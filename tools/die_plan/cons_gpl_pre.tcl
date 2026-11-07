# GENERATED-COPY of tools/die_plan/cons_gpl_pre.tcl (PRE_GLOBAL_PLACE hook of OT_CONS_KIT=1 kits only, KW-FIX-24/CONSKIT
# 11-06): the conservative re-kit caps PLACE_DENSITY at OT_CONS_UTIL (gen_phys.cons_kit_apply).  The plan outline is
# fixed, so a cap below the cell area would stop GPL (GPL-0302 target density below utilization): the density is
# raised to GPL's own uniform-density lower bound + 0.01 in that case and the line OT_CONS_KIT says so.  Then the
# standard hook (face_flops.tcl) runs unchanged.
set cgp_dir [file dirname [file normalize [info script]]]
proc ot_cons_density_floor {} {
  set pad 0
  if {[info exists ::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT)] && $::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT) ne ""} {
    set pad $::env(CELL_PAD_IN_SITES_GLOBAL_PLACEMENT)
  }
  set pd $::env(PLACE_DENSITY)
  if {[catch {gpl::get_global_placement_uniform_density -pad_left $pad -pad_right $pad} lb]} {
    puts "OT_CONS_KIT: WARNING uniform density not available ($lb): PLACE_DENSITY $pd unchanged"
    return
  }
  set need [expr {ceil(($lb + 0.01) * 100.0) / 100.0}]
  if {$pd < $need} {
    puts [format "OT_CONS_KIT density cap %s below cell utilization %.4f: PLACE_DENSITY %.2f (lower bound + 0.01)" $pd $lb $need]
    set ::env(PLACE_DENSITY) [format %.2f $need]
  } else {
    puts [format "OT_CONS_KIT density PLACE_DENSITY %s (cell utilization %.4f)" $pd $lb]
  }
}
ot_cons_density_floor
source [file join $cgp_dir face_flops.tcl]
