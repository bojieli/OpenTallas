# ot_v41_pqc_spine_screen v15 HIER composition PDN (el1011-ds-misc/pqc 2026-10-11) = the engram_c_h recipe:
# physical/s81_ph_views/common/pdn_view.tcl for the top-level cells + M8 straps over the whole outline (connected to
# its M7), and one macro grid over the hardened tiles (views routed with pdn_view.tcl / pdn_view_sram.tcl: OBS M1..M7,
# VDD / VSS pins on M7) connecting each tile's M7 pins to the M8 straps.  Halo 2 (halo 5 fails PDN-0008); a tile grid
# without the M8 layer above it fails PDN-0232/0233.
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
add_pdn_stripe -grid {top} -layer {M8} -width {0.32} -spacing {5.08} -pitch {10.8} -offset {2.0}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -macro -cells {ot_dsrom_aq12t ot_pqc_t_ix ot_pqc_t_qb ot_pqc_t_ret ot_pqc_t_bc ot_pqc_t_ctl16 ot_pqc_t_srom ot_pqc_t_prom ot_pqc_t_xin} -halo {2 2 2 2} -voltage_domains {CORE} -name {pqc_tiles}
add_pdn_connect -grid {pqc_tiles} -layers {M7 M8}
