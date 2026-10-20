# Runs only on the private keep-only source, immediately after fresh link.
# There is no path that clears an existing protection flag.
source [file join [file dirname [info script]] graph_guard.tcl]
set block [ord::get_db_block]
pvm_bf_guard pre_synth_before_pg
foreach i [pvm_bf_cells $block] {if {[$i isDoNotTouch]} {error "PVM_BF_ALREADY_PROTECTED [$i getName]"}}
if {[llength [$block getGlobalConnects]]} {error PVM_BF_UNEXPECTED_PREEXISTING_PG_RULES}
# Literal five rules from smh_pvm_ref_s7a/pdn.tcl, before protection birth.
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSSE$}
global_connect
source $::env(PVM_BF_PG_HELPER)
ot_pg_assert_all_native $block [ot_pg_prepare $block]
pvm_bf_guard pre_synth_after_pg
set private_nets [pvm_bf_private_data_nets $block]
if {[llength $private_nets] != 55440} {error "PVM_BF_PRIVATE_DATA_COUNT [llength $private_nets] expected=55440"}
set inventory [open [file join $::env(PVM_BF_RECEIPTS) private_data_nets.tcllist] {WRONLY CREAT EXCL}]
set names {}; foreach n $private_nets {lappend names [$n getName]}
puts $inventory [lsort $names]; close $inventory
foreach i [pvm_bf_cells $block] {$i setDoNotTouch true}
foreach n $private_nets {$n setDoNotTouch true}
pvm_bf_guard pre_synth_after_protect
ot_pg_assert_all_native $block [ot_pg_prepare $block]
puts "PVM_BF_PROTECT_PASS cells=56000 private_data_nets=[llength $private_nets]"
