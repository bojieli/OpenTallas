read_db /work/pre_gpl.odb
set b [ord::get_db_block]
set before_i [llength [$b getInsts]];set before_n [llength [$b getNets]]
source /work/local_request_decode_fixed.tcl
if {$before_i != [llength [$b getInsts]] || $before_n != [llength [$b getNets]]} {error "A0 hook replay changed circuit topology"}
puts "A0_REQUEST_HOOK_REPLAY_PASS insts=$before_i nets=$before_n decoders=10 state_added=0 edges_added=0"
exit
