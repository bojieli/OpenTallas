# Element-level power grid of ot_hbm_accel_smh (pdn_sm.tcl without the M5 / M6 core stripes): the parent holds only
# abutment channels whose signal pins sit on M4 / M5 at the piece edges, so the channel grid is M1 / M2 rails tied up
# to M7 / M8 straps; hardened pieces expose power on M6 (M6-M7 vias).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}

define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M8}
# (m3 top) the ring fits the 1.08 um core margin: 2 x 0.416 + 0.096 + 0.1 = 1.028 (legal M7/M8 width 0.416) (0.544 widths + 0.5 offset needed 1.684: PDN-0351)
add_pdn_ring -grid {top} -layers {M7 M8} -widths {0.416 0.416} -spacings {0.096} -core_offset {0.1}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M7} -width {0.544} -spacing {0.096} -pitch {21.6} -offset {3.0} \
  -extend_to_core_ring
add_pdn_stripe -grid {top} -layer {M8} -width {0.544} -spacing {0.096} -pitch {21.6} -offset {3.0} \
  -extend_to_core_ring
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M7}
add_pdn_connect -grid {top} -layers {M7 M8}

source $::env(SCRIPTS_DIR)/util.tcl
set blocks {}
foreach inst [find_macros] {
  dict set blocks [[$inst getMaster] getName] 1
}
if {[llength [dict keys $blocks]] > 0} {
  define_pdn_grid -macro -cells [dict keys $blocks] -halo {1 1 1 1} -voltage_domains {CORE} -name {blocks}
  add_pdn_connect -grid {blocks} -layers {M6 M7}
}
