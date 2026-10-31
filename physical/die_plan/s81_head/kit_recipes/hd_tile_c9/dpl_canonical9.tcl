set_thread_count 4
read_db /work/diag_canonical8/3_place.odb
set ff_blk [ord::get_db_block]
source /work/canonical9_invperm.tcl
write_db /work/diag_canonical9/anchored.odb
set rc [catch {detailed_placement} msg]
write_db /work/diag_canonical9/after_dpl.odb
set cc [catch {check_placement -verbose} cm]
puts "CANONICAL9 DPL=$rc $msg CHECK=$cc $cm"
if {$rc || $cc} {exit 1}
write_db /work/diag_canonical9/3_place.odb
