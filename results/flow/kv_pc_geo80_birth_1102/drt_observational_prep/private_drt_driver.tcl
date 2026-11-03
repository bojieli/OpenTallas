# PC private observational DRT; no generic atomic-birth admission.
unset -nocomplain ::pc_drt_no_birth_full_body_pass
set pc_drt_code [catch {source $::env(SCRIPTS_DIR)/detail_route.native_pg_original.tcl} pc_drt_result pc_drt_options]
set pc_drt_cleanup_code 0
if {[info commands ot_native_pg_status] ne ""} {
  set pc_drt_cleanup_code [catch {
    if {[dict get [ot_native_pg_status] active]} {ot_pg_native_birth_end}
  } pc_drt_cleanup pc_drt_cleanup_options]
}
if {$pc_drt_cleanup_code} {puts stderr "PC_DRT_BODY_COMPLETION code=$pc_drt_code result=$pc_drt_result"}
if {$pc_drt_code == 1} {
  if {$pc_drt_cleanup_code} {puts stderr "PC_DRT_CLEANUP_REFUSED $pc_drt_cleanup"}
  return -options $pc_drt_options $pc_drt_result
}
if {$pc_drt_cleanup_code == 1} {return -options $pc_drt_cleanup_options $pc_drt_cleanup}
if {$pc_drt_cleanup_code != 0} {error "PC_DRT_NONLOCAL_CLEANUP_REFUSED $pc_drt_cleanup_code"}
if {$pc_drt_code != 0} {error "PC_DRT_NONLOCAL_BODY_REFUSED $pc_drt_code"}
if {![info exists ::pc_drt_no_birth_full_body_pass] || !$::pc_drt_no_birth_full_body_pass} {error PC_DRT_BEFORE_SAVE_NOT_REACHED}
if {[dict get [ot_native_pg_status] active]} {error PC_DRT_CALLBACK_STILL_ACTIVE}
set saved $::env(RESULTS_DIR)/5_2_route.odb
if {![file exists $saved] || [file size $saved] == 0} {error PC_DRT_OUTPUT_MISSING}
puts "PC_DRT_OBSERVATIONAL_NO_BIRTH_COMPLETE active=0"
