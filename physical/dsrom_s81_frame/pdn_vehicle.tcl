# CLAUDE S81-RERUN die-context vehicles (frame block, macro context): PG grid that reaches every real abstract.
# Base = tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl (M1/M2 rails, M5 2.7 um, M6 5.4 um, M7 10.8 um) plus M8 straps
# over everything; macro grids: the q element exposes VDD/VSS on M7 (the routed Z20c / Z22 abstracts), so its grid
# lands M8 on M7; the cfg ROM (ot_rom_4096x72_m8) has M4 pins, landed from M5.  For STA vehicles (IR is the die cases').
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {2.7} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {10.8} -offset {1.0}
add_pdn_stripe -grid {top} -layer {M8} -width {0.48} -spacing {0.90345} -pitch {10.8} -offset {1.38345}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
add_pdn_connect -grid {top} -layers {M7 M8}
set qcells [list]
set rcells [list]
foreach inst [[ord::get_db_block] getInsts] {
  set m [[$inst getMaster] getName]
  if {[[$inst getMaster] isBlock]} {
    if {[string match "ot_rom_*" $m]} { lappend rcells $m } else { lappend qcells $m }
  }
}
set qcells [lsort -unique $qcells]
set rcells [lsort -unique $rcells]
if {[llength $qcells]} {
  define_pdn_grid -name {q_grid} -voltage_domains {CORE} -macro -cells $qcells -halo {2.0 2.0 2.0 2.0}
  add_pdn_connect -grid {q_grid} -layers {M7 M8}
}
if {[llength $rcells]} {
  define_pdn_grid -name {rom_grid} -voltage_domains {CORE} -macro -cells $rcells -halo {2.0 2.0 2.0 2.0}
  add_pdn_connect -grid {rom_grid} -layers {M4 M5}
}
