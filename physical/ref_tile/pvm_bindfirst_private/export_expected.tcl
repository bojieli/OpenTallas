# Read-only frozen reference export. All endpoint identities remain explicit.
source [file join [file dirname [info script]] graph_guard.tcl]
read_db $::env(PVM_BF_ORIGINAL_ODB)
set f [open $::env(PVM_BF_EXPECTED) {WRONLY CREAT EXCL}]
puts $f [pvm_bf_graph [ord::get_db_block]]
close $f
puts "PVM_BF_REFERENCE_EXPORTED cells=56000"
