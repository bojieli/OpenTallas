# el1011-hbm-no3 2026-10-11: power grid of the HIER W2 rb station top (preamble 'PARENT PDN FOR HARD TILES'; reference
# physical/hgi_idx_hier/pdn_hier.tcl, claude/el1011-hbm-idx bf2d92ae0).  The hard slice tiles ot_hbm_w2_stn_slice8 /
# ot_hbm_w2_stn_slice5 were built on the ORFS default grid and expose M6 power pins (views_hier/*.lef: VDD/VSS on M6),
# so the parent straps them M6-M7; the platform default parent grid connects macros M4-M5 only (PDN-0233).
# Parent: M1/M2 rails, M5/M6 stripes (ASAP7 platform widths / pitches), M7 straps as the station's power pins.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
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
define_pdn_grid -name {slice_m6} -voltage_domains {CORE} -macro \
  -cells {ot_hbm_w2_stn_slice8 ot_hbm_w2_stn_slice5} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
add_pdn_connect -grid {slice_m6} -layers {M6 M7}
