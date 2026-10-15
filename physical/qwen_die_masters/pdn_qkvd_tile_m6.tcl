# el1011-q-kvd 2026-10-11: PDN of a hardened KV-die sub-tile (ot_qkvd_sbuf / ot_qkvd_fbuf8).  Layer contract: the tile
# routes M2-M6 and exposes VDD / VSS as M6 straps; the parent owns M7 (pdn_qkvd_parent_m7.tcl straps M7 onto them).
# Grid = pdn_m5 (M1/M2 rails, M5 stripes) + M6 straps; SRAM macros (sbuf) connect M4/M5 as in pdn_m5.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M6}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {2.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
source $::env(SCRIPTS_DIR)/util.tcl
if {[llength [find_macros]] > 0} {
  define_pdn_grid -name {CORE_macro_grid_1} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0} -default
  add_pdn_connect -grid {CORE_macro_grid_1} -layers {M4 M5}
}
