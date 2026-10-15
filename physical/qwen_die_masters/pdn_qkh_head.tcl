# el1011-q-kvd-head 2026-10-11: PDN of the hierarchical head tile (ot_qwen_nearhbm_head_hs).  The hardened sub-tiles
# (ot_qkh_*) route M2-M6 with VDD / VSS on M6 (pdn_qkh_sub.tcl); the head owns M7 (straps every 10.8 um, pins M7) and
# connects them down onto the sub-tile M6 pins; its own standard cells take M1 / M2 rails and M5 / M6 straps.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_ring -grid {top} -layers {M5 M6} -widths {0.12 0.288} -spacings {0.072 0.096} -core_offset {0.3}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {1.5} -extend_to_core_ring
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {2.0} -extend_to_core_ring
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {3.0}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
source $::env(SCRIPTS_DIR)/util.tcl
set subs {}
foreach inst [find_macros] { dict set subs [[$inst getMaster] getName] 1 }
if {[llength [dict keys $subs]] > 0} {
  define_pdn_grid -macro -cells [dict keys $subs] -halo {2 2 2 2} -voltage_domains {CORE} -name {subs}
  add_pdn_connect -grid {subs} -layers {M6 M7}
}
