from pathlib import Path
import hashlib,sys
root=Path('/work');entry=Path(sys.argv[1])
expected=(root/'native_pg_entry_original.tcl').read_bytes()
actual=entry.read_bytes()
assert actual==expected,'actual ORFS post-MM entry differs from frozen reviewed source'
marker=b'load_design 4_cts.odb 4_cts.sdc\n'
assert actual.count(marker)==1
prefix,body=actual.split(marker,1)
(root/'native_pg_entry_body.tcl').write_bytes(body)
wrapper=r'''
# Exact reviewed seam: libs/DB/SDC/RC loaded; before ALL original PRE/repair body.
if {![info exists ::env(OT_PG_STRICT)] || $::env(OT_PG_STRICT) ne "1"} {error PC_NATIVE_PG_STRICT_REQUIRED}
source /work/native_pg_binding.tcl
ot_pg_native_birth_begin /work/nativepgbirth.so
set pc_geo80_body_code [catch {source /work/native_pg_entry_body.tcl} pc_geo80_body_result pc_geo80_body_options]
set pc_geo80_end_code [catch {ot_pg_native_birth_end} pc_geo80_end_result pc_geo80_end_options]
if {$pc_geo80_end_code} {
  puts stderr "PC_NATIVE_BODY_COMPLETION code=$pc_geo80_body_code result=$pc_geo80_body_result"
  if {$pc_geo80_end_code == 1} {return -options $pc_geo80_end_options $pc_geo80_end_result}
  error "PC_NATIVE_NONLOCAL_CLEANUP_REFUSED code=$pc_geo80_end_code result=$pc_geo80_end_result"
}
set pc_geo80_status [ot_native_pg_status]
if {![dict exists $pc_geo80_status active] || [dict get $pc_geo80_status active]} {error PC_NATIVE_PG_CALLBACK_STILL_ACTIVE}
# Only the unique post-repair checkpoint stop is expected; an ordinary error,
# early normal return, failed audit or failed cleanup cannot become success.
if {$pc_geo80_body_code != 1 || ![dict exists $pc_geo80_body_options -errorcode] || [dict get $pc_geo80_body_options -errorcode] ne {PC_GEO80 CHECKPOINT_READY}} {
  if {$pc_geo80_body_code == 1} {return -options $pc_geo80_body_options $pc_geo80_body_result}
  if {$pc_geo80_body_code != 0} {error "PC_NATIVE_NONLOCAL_BODY_REFUSED code=$pc_geo80_body_code result=$pc_geo80_body_result"}
  error PC_NATIVE_REPAIR_CHECKPOINT_NOT_REACHED
}
foreach f {/work/repair_checkpoint.odb /work/repair_checkpoint.def /work/repair_checkpoint.v /work/REPAIR_CHECKPOINT} {
  if {![file exists $f] || [file size $f] == 0} {error "PC_NATIVE_REPAIR_MISSING_CHECKPOINT $f"}
}
set pc_geo80_receipt [open /work/PG_BIRTH_CLEANUP_PASS w]
puts $pc_geo80_receipt [list receipt $pc_geo80_end_result status $pc_geo80_status active 0]
close $pc_geo80_receipt
puts "PC_NATIVE_PROTECTED_REPAIR_CHECKPOINT_READY active=0"
exit 0
'''
entry.write_bytes(prefix+marker+wrapper.encode())
print('PC_NATIVE_ENTRY_PATCH',hashlib.sha256(actual).hexdigest(),'whole original body preserved',len(body))
