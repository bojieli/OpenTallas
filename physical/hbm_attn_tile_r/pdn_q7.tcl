# OPTION B (HBM-ABSTRACTS coordinator 2026-10-06, IR of the M9-exposed quad failed): the quad's power grid tops out at
# M7 -- the die PDN contract grid (physical/hbm_accel_die_views/common/pdn_view.tcl: M1/M2 rails, M5, M6, M7 PG pin
# stripes 0.288 um @ 10.8 um, VDD x = 1.0, VSS x = 6.4), signal routing M2-M7, M8/M9 left to the die.  The leaves
# (re-hardened with routing <= M6, PG pins M6: leaf_b) take M6 -> M7 vias from the quad's M7 stripes over them.
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
define_pdn_grid -macro -cells {ot_attn_hgrp_m6h1} -halo {5 5 5 5} -voltage_domains {CORE} -name {attn_heads}
add_pdn_connect -grid {attn_heads} -layers {M6 M7}
