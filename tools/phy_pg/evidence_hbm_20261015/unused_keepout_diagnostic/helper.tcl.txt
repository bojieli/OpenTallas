# Declared HBM PG interface preflight and temporary parent-PDN signal keepouts.
# Never edits macro pins/OBS. Keepouts prevent power metal covering actual M8
# clock/reset pins, and are removed in the caller's pdngen finally block.
namespace eval ot_hbm_pg {variable keepouts {}}
proc ot_hbm_pg::restore {} {
  variable keepouts
  foreach obs $keepouts {odb::dbObstruction_destroy $obs}
  set keepouts {}
}
proc ot_hbm_pg::begin {} {
  variable keepouts
  if {[llength $keepouts]} {error "OT_HBM_PG: signal keepouts already active"}
  set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron];set count 0
  foreach inst [$block getInsts] {
    set master [$inst getMaster]
    if {![regexp {^(OT_PDN_BBOX_)?qkd_hbm3e_phy_pc$} [$master getName]]} continue
    foreach net {VDD VSS} {
      set mt [$master findMTerm $net];set layers {}
      if {$mt eq "NULL"} {error "OT_HBM_PG: missing declared $net on [$inst getName]"}
      foreach pin [$mt getMPins] {foreach box [$pin getGeometry] {lappend layers [[$box getTechLayer] getName]}}
      if {[lsort -unique $layers] ne "M4"} {error "OT_HBM_PG: actual $net interface must be M4-only"}
    }
    foreach it [$inst getITerms] {
      set mt [$it getMTerm]
      if {[$mt getSigType] in {POWER GROUND}} continue
      set shapes {};set upper 0
      foreach pin [$mt getMPins] {foreach box [$pin getGeometry] {
        lappend shapes $box
        if {[[$box getTechLayer] getName] eq "M8"} {set upper 1}
      }}
      if {!$upper} continue
      if {[llength $shapes]!=1} {error "OT_HBM_PG: unsupported multi-shape upper signal"}
      set box [$it getBBox];set halo [expr {round(.16*$dbu)}]
      set layer [[ord::get_db_tech] findLayer M8]
      lappend keepouts [odb::dbObstruction_create $block $layer [expr {[$box xMin]-$halo}] [expr {[$box yMin]-$halo}] [expr {[$box xMax]+$halo}] [expr {[$box yMax]+$halo}]]
    }
    incr count
  }
  if {!$count} {error "OT_HBM_PG: no actual native HBM PHY instances"}
  puts "OT_HBM_PG instances=$count M4_VDD_VSS=PASS temporary_M8_signal_keepouts=[llength $keepouts]"
}
