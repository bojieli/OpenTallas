# el1011-hbm-idx 2026-10-11: power grid of a HIERARCHICAL parent whose hard sub-elements (ot_hgi_topk_heap_tile,
# ot_hdc_v41x_idx_hslice, ot_hgi_coll_tkm_tile) were built with physical/qwen_slab_m5/pdn_m5.tcl: their power pins are M5
# stripes, so the parent must strap them from M6 (pdn_m5 alone stops at M5 and connects macros M4-M5 only -> PDN-0233).
# The heap tile (pdn_m5) exposes M5 power pins and leaves M6+ free -> strapped M5-M6; the indexer slice and the
# TOPK_MERGE tile (ORFS default grid) expose M6 power pins -> strapped M6-M7.  Parent: M1/M2 rails, M5/M6 stripes
# (ASAP7 platform widths / pitches), M7 straps (10.8 um) as the parent's power pins for the die grid; SRAMs M4-M5.
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
define_pdn_grid -name {hard_m5} -voltage_domains {CORE} -macro \
  -cells {ot_hgi_topk_heap_tile} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
add_pdn_connect -grid {hard_m5} -layers {M5 M6}
define_pdn_grid -name {hard_m6} -voltage_domains {CORE} -macro \
  -cells {ot_hdc_v41x_idx_hslice ot_hgi_coll_tkm_tile} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
add_pdn_connect -grid {hard_m6} -layers {M6 M7}
define_pdn_grid -name {sram} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0} -default
add_pdn_connect -grid {sram} -layers {M4 M5}
