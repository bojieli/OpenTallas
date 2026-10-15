# el1011-q-kvd 2026-10-11: PDN of a KV-die die master built from hardened sub-tiles (ot_qkvd_sbuf / ot_qkvd_fbuf8 views:
# routed M2-M6, power on M6).  The parent owns M7: M7 straps over the whole core land on the tiles' M6 straps (tile grid
# M6/M7); standard-cell area keeps the pdn_m5 grid (M1/M2 rails, M5 stripes) plus M6 straps to reach M7.  Pins on M5
# (the die-master contract of pdn_m5) and M7.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M5 M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {2.0}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {3.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
source $::env(SCRIPTS_DIR)/util.tcl
set tiles {}
foreach inst [find_macros] { dict set tiles [[$inst getMaster] getName] 1 }
if {[llength [dict keys $tiles]] > 0} {
  define_pdn_grid -macro -cells [dict keys $tiles] -halo {2 2 2 2} -voltage_domains {CORE} -name {tiles}
  add_pdn_connect -grid {tiles} -layers {M6 M7}
}
