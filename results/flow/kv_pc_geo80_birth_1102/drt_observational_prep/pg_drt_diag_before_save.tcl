# BEFORE normal5_2 save. Unexpected births fail this observational scope.
# They were not atomically prohibited; no such capability is claimed.
set ::ot_pg_drt_diag_receipt [ot_native_pg_audit]
foreach field {creates swaps bound} {
  if {[dict get $::ot_pg_drt_diag_receipt $field] != 0} {error "DRT_DIAG_OBSERVED_NATIVE_BIRTH $::ot_pg_drt_diag_receipt"}
}
if {[ot_pg_drt_diag_instances] ne $::ot_pg_drt_diag_input_instances} {error DRT_DIAG_INSTANCE_MASTER_POSE_STATUS_OR_SOURCE_CHANGED}
if {[ot_pg_drt_diag_library_inventory] ne $::ot_pg_drt_diag_input_libraries} {error DRT_DIAG_LOADED_LIBRARY_MASTER_INVENTORY_CHANGED}
ot_pg_native_birth_end
puts "DRT_DIAG_NO_NEW_INSTANCE_OBSERVED $::ot_pg_drt_diag_receipt"
unset ::ot_pg_drt_diag_input_instances ::ot_pg_drt_diag_input_libraries

set ::pc_drt_no_birth_full_body_pass 1
