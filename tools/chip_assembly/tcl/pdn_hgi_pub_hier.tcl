# el1011-hbm-smh/pub: PDN of the HIER SM publication parent (ot_hgi_sm_pub_hier; copy of pdn_smh_tile_hier.tcl).  The
# hardened slices route M2-M6 and expose VDD / VSS on M6; the parent owns M7 (straps every 10.8 um) and drops them on.
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
set srams {}
set cols {}
foreach inst [find_macros] {
  set m [[$inst getMaster] getName]
  if {[string match {ot_hgi_sm_pub_slice} $m]} { dict set cols $m 1 } else { dict set srams $m 1 }
}
if {[llength [dict keys $srams]] > 0} {
  define_pdn_grid -macro -cells [dict keys $srams] -halo {2 2 2 2} -voltage_domains {CORE} -name {mems}
  add_pdn_connect -grid {mems} -layers {M4 M5}
}
if {[llength [dict keys $cols]] > 0} {
  define_pdn_grid -macro -cells [dict keys $cols] -halo {2 2 2 2} -voltage_domains {CORE} -name {cols}
  add_pdn_connect -grid {cols} -layers {M6 M7}
}
