# Element-specific clock architecture: one ot_cg_tile ICG plus the balanced
# clock_spine on its GCLK net. Generic ICG cloning would replace that root
# with 256 gates before the through-ICG spine resolves it (r1 CTS failure).
# Preserve the exact functional clock gate and use the supported single-root
# spine distribution; no RTL, ENA, HOLD counter, latency or clock constraint change.
set smn_root_gate {u.u_cgt.u_cg.u_icg}
set smn_inst [[ord::get_db_block] findInst $smn_root_gate]
if {$smn_inst eq "NULL" || $smn_inst eq ""} {
  error "SM_NATIVE_ROOT_GATE: expected root gate $smn_root_gate missing"
}
if {![string match ICG* [[$smn_inst getMaster] getName]]} {
  error "SM_NATIVE_ROOT_GATE: $smn_root_gate is not an ICG"
}
if {![info exists ::ot_cg_exclude]} { set ::ot_cg_exclude {} }
lappend ::ot_cg_exclude $smn_root_gate
puts "SM_NATIVE_ROOT_GATE: preserve one $smn_root_gate for balanced GCLK spine"
