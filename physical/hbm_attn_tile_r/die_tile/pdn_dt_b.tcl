# pdn_dt_b (el1011-hbm-attn 2026-10-12, half v12): pdn_dt.tcl with the bank macro grid over EVERY bank master the
# block contains (sn544 / ew544 / sn136 / ew136; pdn_dt listed only the 544-bit banks, so the 136-bit banks' M6 PG pins
# got no M6 -> M7 strap vias).  A grid is created only for masters present (PDN-0217 rule).
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
set ot_bk_present {}
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_mn [[$ot_i getMaster] getName]
  if {[string match ot_attn_bank_* $ot_mn] && [lsearch -exact $ot_bk_present $ot_mn] < 0} { lappend ot_bk_present $ot_mn }
}
puts "OT_PDN_DT_B bank masters: $ot_bk_present"
if {[llength $ot_bk_present]} {
  define_pdn_grid -macro -cells $ot_bk_present -halo {1 1 1 1} -voltage_domains {CORE} -name {banks}
  add_pdn_connect -grid {banks} -layers {M6 M7}
}
