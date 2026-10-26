# el1011-hbm-coll 2026-10-11 (preamble PARENT PDN FOR HARD TILES + UPDATEs 1/2): pdn_view.tcl for a die view whose children are
# HARD tiles.  pdn_view.tcl defines only the core grid, so a hard child's M6 power pins (ot_hbm_link_retry_pipeline in hfd_lk_ep,
# ot_hcoll_port tiles in the hierarchical hfd_coll) were never strapped (prior hfd_lk_ep PDN logs: "Inserting grid: top" only).
# Same core grid as pdn_view.tcl, plus macro grids created ONLY when the master is present (PDN-0217 otherwise):
#   hard_m6 : M6 power-pin hard children, strapped from M7 (M6-M7), halo 2 um, every orientation (hfd_lk_ep mirrors macro 2)
#   sram    : ot_sram_* M4-M5 (default macro grid)
# Child abstracts must be exact-shape (no -bloat_occupied_layers, UPDATE 2): view_export.py writes them that way.
# CLAUDE HBM-ABSTRACTS die view PDN = the HBM die PDN contract (tools/dsrom_s81_fulldie.py _gen_pg_lef / case_irm, the
# model the r16g IR verdict was measured with): the die owns M8/M9 (bump-aligned straps); every block exposes M7 PG
# stripes 0.288 um wide on a 10.8 um pitch (VDD at x = 1.0, VSS at x = 6.4 + k * 10.8) that the die grid drops onto
# through M7-M8 vias.  Inside: M1/M2 rails, M5 straps, M6 straps, M7 stripes.  Signals route M2-M7 (route_view.sh
# MAXL), so the view leaves M8/M9 to the die.  A view whose hard sub-macros carry M8/M9 PG breaks this contract:
# report it as a defect (the sub-block must be re-hardened with its PDN top at M7).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}

proc ot_view_has_master {pats} {
  foreach inst [[ord::get_db_block] getInsts] {
    set m [[$inst getMaster] getName]
    foreach p $pats { if {[string match $p $m]} { return 1 } }
  }
  return 0
}
set ot_hard_m6 {}
foreach c {ot_hbm_link_retry_pipeline ot_hcoll_port} { if {[ot_view_has_master $c]} { lappend ot_hard_m6 $c } }
if {[llength $ot_hard_m6]} {
  define_pdn_grid -name {hard_m6} -voltage_domains {CORE} -macro -cells $ot_hard_m6 -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
  add_pdn_connect -grid {hard_m6} -layers {M6 M7}
}
if {[ot_view_has_master {ot_sram_*}]} {
  define_pdn_grid -name {sram} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0} -default
  add_pdn_connect -grid {sram} -layers {M4 M5}
}
