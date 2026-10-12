# el1011-q-tile 2026-10-11: power grid of the round-2 HIERARCHICAL tile parent (qfd_tile_h2 / qfd_tile_e_h2), per the
# PARENT PDN FOR HARD TILES rule (reference physical/hgi_idx_hier/pdn_hier.tcl, el1011-hbm-idx bf2d92ae0).  The flat tile's
# pdn_m5.tcl stops at M5 and connects macros M4-M5 only; the hardened lane-slice leaves (ot_qwen_tile_lsl, ORFS default grid)
# expose M6 power pins -> PDN-0233.  Parent: M1/M2 rails, M5/M6 stripes (ASAP7 platform widths / pitches), M7 straps
# (10.8 um) as the tile's power pins for the die grid (M8/M9 over the top); ROM / KV SRAM macros (M4 pins) M4-M5; leaves M6-M7.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
define_pdn_grid -name {hard_lsl} -voltage_domains {CORE} -macro \
  -cells {ot_qwen_tile_lsl} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
add_pdn_connect -grid {hard_lsl} -layers {M6 M7}
define_pdn_grid -name {sram} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0} -default
add_pdn_connect -grid {sram} -layers {M4 M5}
