# CLAUDE el1011-ds-mtp (dsfd_mtp_hrow rev 3) view PDN: the S81 view PDN contract (common/pdn_view.tcl: M1/M2 rails, M5/M6
# straps, M7 stripes 0.288 um on 10.8 um, M8/M9 left to the die) plus a macro grid for the 30 hardened banks
# dsfd_mtp_hrow_bank (PG pins on M6 + M7, placed on the 10.8 um lattice): the top M7 stripes drop onto the bank's M6
# pins through M6-M7 vias (reference physical/hgi_idx_hier/pdn_hier.tcl, PARENT PDN FOR HARD TILES).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M8}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
# el1011-ds-mtp 10-11: the hard banks own full-length M7 VDD/VSS stripes (their LEF PG pins; signals route around
# them on M7), so the cluster straps ONE layer above: horizontal M8 straps over the whole outline, M7-M8 vias onto the
# cluster's own M7 stripes and onto every bank's M7 PG stripes (the M6-M7 bank connect found no shapes: PDN-0232/0233)
add_pdn_stripe -grid {top} -layer {M8} -width {0.288} -spacing {0.288} -pitch {10.8} -offset {2.0}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -name {bank} -voltage_domains {CORE} -macro \
  -cells {dsfd_mtp_hrow_bank} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
add_pdn_connect -grid {bank} -layers {M7 M8}
