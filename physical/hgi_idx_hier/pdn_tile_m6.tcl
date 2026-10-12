# el1011-hbm-idx 10-11 ~21:50 LAYER CONTRACT leaf grid for a hard tile with SRAMs: M1/M2 rails, M5/M6 stripes, PG pins = full M6 stripes;
# signals route M2-M6 (RLAYERS), M7 left free for the die/hub straps.  SRAM macros connect M4-M5 (from pdn_hier.tcl).
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
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {5.4} -offset {0.513}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
# Macro grids are created ONLY for masters present in the block: a macro grid with no matching instance is never
# created, so its add_pdn_connect fails (PDN-0217 "No grid found with name" -- the chunk parent has no SRAM).
proc ot_hier_has_master {pats} {
  foreach inst [[ord::get_db_block] getInsts] {
    set m [[$inst getMaster] getName]
    foreach p $pats { if {[string match $p $m]} { return 1 } }
  }
  return 0
}
if {[ot_hier_has_master {ot_hgi_topk_heap_tile}]} {
  define_pdn_grid -name {hard_m5} -voltage_domains {CORE} -macro \
    -cells {ot_hgi_topk_heap_tile} -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
  add_pdn_connect -grid {hard_m5} -layers {M5 M6}
}
set ot_m6 {}
foreach c {ot_hdc_v41x_idx_hslice ot_hgi_coll_tkm_tile} { if {[ot_hier_has_master $c]} { lappend ot_m6 $c } }
if {[llength $ot_m6]} {
  define_pdn_grid -name {hard_m6} -voltage_domains {CORE} -macro -cells $ot_m6 -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0}
}
if {[ot_hier_has_master {ot_sram_*}]} {
  define_pdn_grid -name {sram} -voltage_domains {CORE} -macro -orient {R0 R180 MX MY} -halo {2.0 2.0 2.0 2.0} -default
  add_pdn_connect -grid {sram} -layers {M4 M5}
}
