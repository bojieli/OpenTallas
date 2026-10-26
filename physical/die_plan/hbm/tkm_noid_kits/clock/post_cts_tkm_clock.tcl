# F4 only rewires local flop clock leaves; no legacy tap-input alignment.
source /work/f4_chain_leaf.tcl
# Balance means after F4 has finished, preserving the selected graph/topology.
ot_dtsh::closed_loop {*}$::ot_dtsh::cl_args measure_sinks _sink
ot_dtsh::audit
ot_hbmentry::check
# Audit passed with existing cells held FIRM; give later stages normal freedom.
if {![info exists ::ot_tkm_cts_firm]} { error "TKM CTS hold list missing: pre-CTS hold did not run" }
foreach ot_tkm_name $::ot_tkm_cts_firm {
  set ot_tkm_inst [$::dt_blk findInst $ot_tkm_name]
  if {[$ot_tkm_inst getPlacementStatus] ne "FIRM"} { error "TKM CTS hold: $ot_tkm_name lost FIRM before release" }
  $ot_tkm_inst setPlacementStatus PLACED
}
puts "OT_TKM_CTS_HOLD released [llength $::ot_tkm_cts_firm] existing placements to PLACED after OT_DTSH audit"
