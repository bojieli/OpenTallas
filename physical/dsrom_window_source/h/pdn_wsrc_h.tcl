# ot_dsrom_window_source_ctl MARGIN 3 HIER PDN (el1011-ds-misc 2026-10-11) = physical/s81_ph_views/common/pdn_view.tcl + a macro grid for the hardened leaves (engram_c_h recipe)
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
# leaves (ot_dsrom_wsrc_land8 / ot_dsrom_wsrc_mirror views, routed M2-M7: OBS M1..M7, VDD / VSS pins on M6 / M7 with M7 vertical
# stripes at pitch 10.8): the ORFS BLOCKS recipe one layer up -- the top grid carries M8 straps over the whole outline
# (connected to its M7), and the leaf grid connects each leaf's M7 pins to those M8 straps (PDN-0232/0233 otherwise:
# a leaf grid with only a connect and no layer above the leaf's obstructions has no shapes).
add_pdn_stripe -grid {top} -layer {M8} -width {0.32} -spacing {5.08} -pitch {10.8} -offset {2.0}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -macro -cells {ot_dsrom_wsrc_land8 ot_dsrom_wsrc_mirror} -halo {2 2 2 2} -voltage_domains {CORE} -name {wsrc_leaves}
add_pdn_connect -grid {wsrc_leaves} -layers {M7 M8}
