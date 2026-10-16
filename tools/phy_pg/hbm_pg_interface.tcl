# Validate the NEW declared external HBM power interface before PDN generation.
# This changes no geometry and makes historical missing-power LEFs fail closed.
namespace eval ot_hbm_pg {}
proc ot_hbm_pg::check {} {
  set count 0
  foreach inst [[ord::get_db_block] getInsts] {
    set master [$inst getMaster]
    if {![regexp {^(OT_PDN_BBOX_)?qkd_hbm3e_phy_pc$} [$master getName]]} continue
    foreach net {VDD VSS} {
      set mt [$master findMTerm $net];set layers {}
      if {$mt eq "NULL"} {error "OT_HBM_PG: missing declared $net on [$inst getName]"}
      foreach pin [$mt getMPins] {foreach box [$pin getGeometry] {lappend layers [[$box getTechLayer] getName]}}
      if {[lsort -unique $layers] ne "M4"} {error "OT_HBM_PG: actual $net interface must be M4-only"}
    }
    incr count
  }
  if {!$count} {error "OT_HBM_PG: no actual native HBM PHY instances"}
  puts "OT_HBM_PG instances=$count M4_VDD_VSS=PASS"
}
