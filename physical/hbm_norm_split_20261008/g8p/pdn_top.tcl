# conservative-1011 2026-10-11 (PARENT PDN FOR HARD TILES; reference physical/hgi_idx_hier/pdn_hier.tcl bf2d92ae0): grid of
# the g8p split-norm top.  The 8 ot_hbm_norm_gtile8 children (g8p/pdn_gtile.tcl) expose M7 power stripes and route
# signals on M7 around them, so the parent adds M5/M6/M7 stripes in the channels/band + M8 straps (the top's power pins)
# and joins each tile M7 -> M8 (hcp/pdn_qt.tcl pattern; preamble UPDATE 2).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M8}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_stripe -grid {top} -layer {M8} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -name {gtiles} -voltage_domains {CORE} -macro -cells {ot_hbm_norm_gtile8} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
add_pdn_connect -grid {gtiles} -layers {M7 M8}
