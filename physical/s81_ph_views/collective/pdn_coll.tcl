# CLAUDE S81-PH collective view PDN: the S81 view PDN contract (common/pdn_view.tcl: M1/M2 rails, M5/M6 straps, M7
# stripes 0.288 um on 10.8 um, M8/M9 left to the die) plus macro grids: the SRAM macros and the PLL reservation have
# their PG pins on M4; M5 straps over them connect down to M4 and up to the top grid's M6 straps.
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
define_pdn_grid -macro -cells {ot_sram_1r1w_512x128_m4_r2c2 ot_sram_1r1w_256x256_m2_r2c2 ot_s81_pll_bb} -halo {2 2 2 2} -voltage_domains {CORE} -name {mac}
add_pdn_stripe -grid {mac} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_connect -grid {mac} -layers {M4 M5}
add_pdn_connect -grid {mac} -layers {M5 M6}
