# hfd_attn_tile_b PDN = the die contract grid (M1/M2 rails, M5, M6, M7 PG pin stripes 0.288 um @ 10.8 um, VDD x = 1.0,
# VSS x = 6.4); the pipeline banks' M6 PG pins take M6 -> M7 vias from the tile stripes over them; the option-B quads
# (PG <= M7) are linked by quad_m7_link.tcl (POST_PDN).  No M8 / M9: the die owns them.
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
define_pdn_grid -macro -cells {ot_attn_bank_sn544 ot_attn_bank_ew544} -halo {1 1 1 1} -voltage_domains {CORE} -name {banks}
add_pdn_connect -grid {banks} -layers {M6 M7}
