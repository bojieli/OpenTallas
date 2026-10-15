# conservative-1011 2026-10-11 (PARENT PDN FOR HARD TILES): grid of the tiled hfd_hc quarter.  The 88 hfd_hc_tile_xl
# children expose their power pins on M7 (tile grid -pins {M7}: VSS x 0.856 / VDD 6.256 mod 10.8 in the tile frame; M6 only
# as edge stubs), so a parent that stops at M7 (su/pdn_quarter.tcl) cannot reach them (PDN-0233).  Parent: M1/M2 rails,
# M5/M6/M7 stripes in the channels and the E band (as pdn_quarter), M8 straps (dsrom_window_columns precedent widths)
# over everything = the quarter's power pins; each tile joined at its own M7 pins from M8.
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
add_pdn_stripe -grid {top} -layer {M8} -width {0.474} -spacing {2.226} -pitch {5.4} -offset {1.5}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
add_pdn_connect -grid {top} -layers {M7 M8}
define_pdn_grid -name {tiles} -voltage_domains {CORE} -macro -cells {hfd_hc_tile_xl} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
add_pdn_connect -grid {tiles} -layers {M7 M8}
