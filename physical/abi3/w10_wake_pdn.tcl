# Baseline closure companion; unchanged geometry/constraint body from d417de733 tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl SHA256 0138cf3dc0193bd86d6a1d2bc5f5c1335fc80c7a0589ee25a498350958852cd6
# W10 ROM-array element / pair power grid, IR fix adopted 2026-09-30 (W18 ir_options.json 34682123): M5 straps at a
# 2.7 um per-net pitch (was 5.4), M7 pins for the parent grid; M6 at 5.4 um (pdn_w10_elem_m7_ir_m6.tcl doubles it).
# Base: the ASAP7 platform default (grid_strategy-M1-M2-M5-M6.tcl) plus
# M7 straps exposed as the block's VDD/VSS pins, so the die-level grid (W18) reaches them over the M7 OBS
# of the abstract.  M1/M2 follow the standard-cell rails, M5/M6 stripes, M7 straps on a 10.8 um pitch.
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
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {2.7} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
define_pdn_grid -name {CORE_macro_grid_1} -voltage_domains {CORE} -macro \
  -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0} -default
add_pdn_connect -grid {CORE_macro_grid_1} -layers {M4 M5}
define_pdn_grid -name {CORE_macro_grid_2} -voltage_domains {CORE} -macro \
  -orient {R90 R270 MXR90 MYR90} -halo {2.0 2.0 2.0 2.0} -default
add_pdn_connect -grid {CORE_macro_grid_2} -layers {M4 M5}
