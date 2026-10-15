# el1011-q-kvd-head 2026-10-11: PDN of a hardened head sub-tile (ot_qkh_lane8 / ot_qkh_ktree).  Layer contract (the
# el1011-hbm-smh lesson, PDN-0006): the sub-tile routes M2-M6 (MAX_ROUTING_LAYER M6) and exposes VDD / VSS as M6 pins;
# the parent head tile (pdn_qkh_head.tcl) owns M7 and drops its straps onto those M6 pins.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M6}
add_pdn_ring -grid {top} -layers {M5 M6} -widths {0.12 0.288} -spacings {0.072 0.096} -core_offset {0.3}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {1.5} -extend_to_core_ring
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {2.0} -extend_to_core_ring
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
