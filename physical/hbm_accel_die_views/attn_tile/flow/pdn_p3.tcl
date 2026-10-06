# hfd_attn_tile PDN (CLAUDE HBM-ABSTRACTS attn) P3 = the die PDN contract (physical/hbm_accel_die_views/common/
# pdn_view.tcl: M1/M2 rails, M5, M6, M7 PG pin stripes 0.288 um @ 10.8 um, VDD x = 1.0, VSS x = 6.4) PLUS the one
# exception the closed quads force: ot_attn_tile_m6h1q carries its own M8/M9 PG (M9 stripe pins, M8 edge stubs), so
# the tile adds M8 straps on the quads' PG lattice (VSS centres y = 4.272 mod 5.4 from the core origin y 0.54, quad
# placement macro_placement.tcl) that meet the quads' M8 PG stubs at their edges and drop to the M7 contract stripes.
# Die consequence (defect recorded in view.json): the tile consumes M8 over its quad rows and M8 / M9 over the four
# quad footprints; the die grid reaches the tile through the M7 stripes.
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
add_pdn_stripe -grid {top} -layer {M8} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {3.732}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
add_pdn_connect -grid {top} -layers {M7 M8}
