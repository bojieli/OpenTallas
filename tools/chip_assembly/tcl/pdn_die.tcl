# Level-3 (die) power grid.  Signals route M2-M9; the tiles expose power on
# M8, the PHY placeholders on M4 (fakeram style).  M1/M2 rails for the die's
# own cells, M5/M6 in the channels, M8/M9 as the die mesh over everything.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}

define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M9}
add_pdn_ring -grid {top} -layers {M8 M9} -widths {1.0 1.0} -spacings {0.5} -core_offset {1.0}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {10.8} -offset {1.5}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {2.0}
add_pdn_stripe -grid {top} -layer {M8} -width {1.0} -spacing {0.5} -pitch {40.0} -offset {5.0} \
  -extend_to_core_ring
add_pdn_stripe -grid {top} -layer {M9} -width {1.0} -spacing {0.5} -pitch {40.0} -offset {5.0} \
  -extend_to_core_ring
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M8}
add_pdn_connect -grid {top} -layers {M8 M9}

source $::env(SCRIPTS_DIR)/util.tcl
set tiles {}
set phys {}
foreach inst [find_macros] {
  set master [[$inst getMaster] getName]
  if {[string match "ot_phy_*" $master]} { dict set phys $master 1 } else { dict set tiles $master 1 }
}
if {[llength [dict keys $phys]] > 0} {
  define_pdn_grid -macro -cells [dict keys $phys] -halo {2 2 2 2} \
    -voltage_domains {CORE} -name {phys}
  add_pdn_connect -grid {phys} -layers {M4 M5}
}
if {[llength [dict keys $tiles]] > 0} {
  define_pdn_grid -macro -cells [dict keys $tiles] -halo {2 2 2 2} \
    -voltage_domains {CORE} -name {tiles}
  add_pdn_connect -grid {tiles} -layers {M8 M9}
}
