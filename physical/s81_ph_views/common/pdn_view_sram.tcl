add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
set ot_sram_cells {}
foreach ot_m [[ord::get_db] getLibs] { foreach ot_c [$ot_m getMasters] {
  if {[$ot_c isBlock] && [string match ot_sram_* [$ot_c getName]]} { lappend ot_sram_cells [$ot_c getName] } } }
if {[llength $ot_sram_cells]} {
  puts "pdn_tile_sym: SRAM macro grid on [lsort -unique $ot_sram_cells]"
  define_pdn_grid -macro -cells [lsort -unique $ot_sram_cells] -halo {2 2 2 2} -voltage_domains {CORE} -name {sram}
  add_pdn_stripe -grid {sram} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
  add_pdn_connect -grid {sram} -layers {M4 M5}
  add_pdn_connect -grid {sram} -layers {M5 M6}
}
