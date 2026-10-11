# dsfd_engram_c HIER PDN = physical/s81_ph_views/common/pdn_view.tcl + a macro grid for the hardened leaves
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
# HIER leaves (closed dsfd_engram_lkp / dsfd_engram_sink views: OBS M1..M7, VDD / VSS pins on M6 / M7 with M7 vertical
# stripes at pitch 10.8): the ORFS BLOCKS recipe one layer up -- the top grid carries M8 straps over the whole outline
# (connected to its M7), and the leaf grid connects each leaf's M7 pins to those M8 straps (PDN-0232/0233 otherwise:
# a leaf grid with only a connect and no layer above the leaf's obstructions has no shapes).
add_pdn_stripe -grid {top} -layer {M8} -width {0.32} -spacing {5.08} -pitch {10.8} -offset {2.0}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -macro -cells {dsfd_engram_lkp dsfd_engram_sink} -halo {2 2 2 2} -voltage_domains {CORE} -name {engram_leaves}
add_pdn_connect -grid {engram_leaves} -layers {M7 M8}
# SRAM macros (OBS M1..M4, VDD / VSS pins on M4): the top grid's M5 straps cross them -> connect M4-M5 (the ORFS macro recipe;
# pdn_view.tcl alone left the 18 SRAM supplies unconnected: PSM-0039 on every u_sram under check_power_grid).
define_pdn_grid -macro -cells {ot_sram_1r1w_256x256_m2_r2c2} -halo {2 2 2 2} -voltage_domains {CORE} -name {engram_srams}
add_pdn_connect -grid {engram_srams} -layers {M4 M5}
