from pathlib import Path
import hashlib,sys
root=Path('/work');entry=Path(sys.argv[1])
expected=(root/'native_pg_entry_original.tcl').read_bytes();actual=entry.read_bytes()
assert actual==expected,'actual post-MM ORFS entry differs from frozen source'
marker=b'load_design 4_cts.odb 4_cts.sdc\n';assert actual.count(marker)==1
prefix,body=actual.split(marker,1);(root/'native_pg_entry_body.tcl').write_bytes(body)
wrapper=r'''
if {![info exists ::env(OT_PG_STRICT)] || $::env(OT_PG_STRICT) ne "1"} {error PC_FRESH_PG_STRICT_REQUIRED}
foreach {k v} {SKIP_INCREMENTAL_REPAIR 1 SKIP_ANTENNA_REPAIR 1 OPT_POST_GRT_WNS 1 RECOVER_POWER 0 GENERATE_ARTIFACTS_ON_FAILURE 0} {
  if {![info exists ::env($k)] || $::env($k) ne $v} {error "PC_FRESH_SCOPE_FLAG $k"}
}
foreach k {OT_MAXWIRE_UM OT_TAP_GRT_MODE} {
  if {[info exists ::env($k)] && $::env($k) ne ""} {error "PC_FRESH_UNEXPECTED_MUTATION $k"}
}
source /work/native_pg_binding.tcl
ot_pg_native_birth_begin /work/nativepgbirth.so
set pc_fresh_code [catch {source /work/native_pg_entry_body.tcl} pc_fresh_result pc_fresh_options]
set pc_fresh_end_code [catch {ot_pg_native_birth_end} pc_fresh_end_result pc_fresh_end_options]
if {$pc_fresh_end_code} {
  puts stderr "PC_FRESH_BODY_COMPLETION code=$pc_fresh_code result=$pc_fresh_result"
  puts stderr "PC_FRESH_CLEANUP_FAILURE code=$pc_fresh_end_code result=$pc_fresh_end_result"
  # Retain the original primary ordinary body error when cleanup also fails.
  if {$pc_fresh_code == 1} {return -options $pc_fresh_options $pc_fresh_result}
  if {$pc_fresh_end_code == 1} {return -options $pc_fresh_end_options $pc_fresh_end_result}
  error "PC_FRESH_NONLOCAL_CLEANUP_REFUSED $pc_fresh_end_code"
}
foreach k {creates swaps bound} {
  if {![dict exists $pc_fresh_end_result $k] || [dict get $pc_fresh_end_result $k] != 0} {error "PC_FRESH_UNEXPECTED_NATIVE_MUTATION $k receipt=$pc_fresh_end_result"}
}
set pc_fresh_status [ot_native_pg_status]
if {![dict exists $pc_fresh_status active] || [dict get $pc_fresh_status active]} {error PC_FRESH_CALLBACK_STILL_ACTIVE}
if {$pc_fresh_code != 0} {
  if {$pc_fresh_code == 1} {return -options $pc_fresh_options $pc_fresh_result}
  error "PC_FRESH_NONLOCAL_BODY_REFUSED $pc_fresh_code"
}
if {![info exists ::pc_fresh_grt_post_complete] || !$::pc_fresh_grt_post_complete} {error PC_FRESH_FULL_POST_NOT_REACHED}
foreach f [list $::env(RESULTS_DIR)/5_1_grt.odb $::env(RESULTS_DIR)/5_1_grt.sdc $::env(RESULTS_DIR)/route.guide /work/reload_post_grt.clock.tsv] {
  if {![file exists $f] || [file size $f] == 0} {error "PC_FRESH_MISSING_OUTPUT $f"}
}
set f [open /work/FRESH_GRT_NATIVE_CLEANUP_PASS w]
puts $f [list receipt $pc_fresh_end_result status $pc_fresh_status active 0 full_post 1]
close $f
puts "PC_FRESH_DPL_DATA_GRT_COMPLETE active=0 full_post=1"
'''
entry.write_bytes(prefix+marker+wrapper.encode())
print('PC_FRESH_ENTRY_PATCH',hashlib.sha256(actual).hexdigest(),'whole original body preserved',len(body))
