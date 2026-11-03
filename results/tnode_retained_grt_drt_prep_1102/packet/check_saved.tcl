# Fresh process, actual saved DRT DB; no global_connect, repair, or routing.
source /work/native_pg_binding.tcl
source /work/tnode_structure_guard.tcl
read_db /work/run/results/asap7/hbc_ot_hnx_fused_tnode/base/5_2_route.odb
set b [ord::get_db_block]
set f [open /work/drt_input_structure.tcldata r]; set before [string trimright [read $f] \n]; close $f
if {[tnode_structure_guard $b] ne $before} {error TNODE_SAVED_DRT_STRUCTURE_CHANGED}
ot_pg_audit_snapshot $b /work/drt_saved_pg.json
ot_pg_assert_all_native $b [ot_pg_prepare $b]
puts TNODE_FRESH_SAVED_DRT_STRUCTURE_EQUAL_PG0
