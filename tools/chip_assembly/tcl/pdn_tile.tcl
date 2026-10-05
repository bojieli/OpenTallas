# Level-2 (tile) power grid.  Signals route M2-M8; the tile exposes its power
# on M8 for the die grid.  M1/M2 rails for the tile's own cells, M5/M6 for
# the glue region and the placeholder memories, M7/M8 over everything.
# Hardened blocks (level 1) expose power on M6: M6-M7 vias.  Placeholder
# memories expose it on M4 like the platform fakeram: M4-M5 vias.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}

define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M8}
add_pdn_ring -grid {top} -layers {M7 M8} -widths {0.544 0.544} -spacings {0.096} -core_offset {0.5}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {1.5}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {2.0}
add_pdn_stripe -grid {top} -layer {M7} -width {0.544} -spacing {0.096} -pitch {21.6} -offset {3.0} \
  -extend_to_core_ring
add_pdn_stripe -grid {top} -layer {M8} -width {0.544} -spacing {0.096} -pitch {21.6} -offset {3.0} \
  -extend_to_core_ring
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
add_pdn_connect -grid {top} -layers {M7 M8}

source $::env(SCRIPTS_DIR)/util.tcl
set blocks {}
set mems {}
foreach inst [find_macros] {
  set master [[$inst getMaster] getName]
  if {[string match "ot_mem_*" $master] || [string match "fakeram*" $master]} {
    dict set mems $master 1
  } else {
    dict set blocks $master 1
  }
}
if {[llength [dict keys $blocks]] > 0} {
  define_pdn_grid -macro -cells [dict keys $blocks] -halo {2 2 2 2} \
    -voltage_domains {CORE} -name {blocks}
  add_pdn_connect -grid {blocks} -layers {M6 M7}
}
if {[llength [dict keys $mems]] > 0} {
  define_pdn_grid -macro -cells [dict keys $mems] -halo {2 2 2 2} \
    -voltage_domains {CORE} -name {mems}
  add_pdn_connect -grid {mems} -layers {M4 M5}
}
