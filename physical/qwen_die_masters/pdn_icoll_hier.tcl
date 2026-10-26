# el1011-q-coll 2026-10-11: power grid of the qfd_io_collective HIERARCHICAL parent (pr2h), from physical/hgi_idx_hier/
# pdn_hier.tcl (el1011-hbm-idx bf2d92ae0).  The hard lane slice ot_coll_fold_slice (routed qfd_io_collective_fs with the
# ORFS default grid) exposes its VDD / VSS pins on M6 (abstract LEF) -> strapped M6-M7; the source-FIFO SRAMs
# (ot_sram_1r1w_32x546_m1) connect M4-M5.  Parent: M1/M2 rails, M5/M6 stripes, M7 straps (the parent's power pins).
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
# el1011-q-coll: each macro grid only when the block holds that master (hbm-idx 8d848821f: an unused macro grid aborts
# with PDN-0217).
proc ot_hier_has_master {pats} {
  foreach inst [[ord::get_db_block] getInsts] {
    set m [[$inst getMaster] getName]
    foreach p $pats { if {[string match $p $m]} { return 1 } }
  }
  return 0
}
if {[ot_hier_has_master {ot_coll_fold_slice}]} {
  define_pdn_grid -name {hard_m6} -voltage_domains {CORE} -macro -cells {ot_coll_fold_slice} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
  add_pdn_connect -grid {hard_m6} -layers {M6 M7}
}
if {[ot_hier_has_master {ot_sram_*}]} {
  define_pdn_grid -name {sram} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0} -default
  add_pdn_connect -grid {sram} -layers {M4 M5}
}
