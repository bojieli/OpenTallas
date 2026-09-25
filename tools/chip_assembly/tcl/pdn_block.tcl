# Level-1 (hardened block) power grid: signals route M2-M6, so the block
# exposes its power on M6 stripes and the parent drops M6-M7 vias on them.
# M1/M2 follow the standard-cell rails, M5 (vertical) and M6 (horizontal)
# stripes, an M5/M6 ring inside the 2 um die margin.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}

define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M6}
add_pdn_ring -grid {top} -layers {M5 M6} -widths {0.12 0.288} -spacings {0.072 0.096} \
  -core_offset {0.3}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} \
  -offset {1.5} -extend_to_core_ring
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {10.8} \
  -offset {2.0} -extend_to_core_ring
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
