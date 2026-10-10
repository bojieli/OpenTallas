# ot_hcoll_port slice PDN (hbm-coll-rtl 2026-10-08): the hfd_vm view grid (common/pdn_view.tcl + the SRAM macro grid)
# with its top at M6, so the hfd_coll top drops its own M7 stripes over every slice instance and connects M7 -> M6
# (rtl_ps/pdn_top.tcl).  Pins on M6; slice signals route M2-M6.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M6}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
define_pdn_grid -macro -cells {ot_sram_1r1w_128x256_m1_r2c2} -halo {2 2 2 2} -voltage_domains {CORE} -name {sram}
add_pdn_stripe -grid {sram} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_connect -grid {sram} -layers {M4 M5}
add_pdn_connect -grid {sram} -layers {M5 M6}
