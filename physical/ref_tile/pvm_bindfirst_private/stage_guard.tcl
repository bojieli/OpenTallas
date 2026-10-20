# The caller sets the exact ORFS stage name. No graph mutation is permitted.
if {![info exists pvm_bf_stage]} {error PVM_BF_UNNAMED_STAGE}
source [file join [file dirname [info script]] graph_guard.tcl]
pvm_bf_guard $pvm_bf_stage
set block [ord::get_db_block]
foreach i [pvm_bf_cells $block] {if {![$i isDoNotTouch]} {error "PVM_BF_PROTECTION_DRIFT $pvm_bf_stage [$i getName]"}}
set f [open [file join $::env(PVM_BF_RECEIPTS) private_data_nets.tcllist] r]; set names [string trimright [read $f] "\n"]; close $f
if {[llength $names] != 55440} {error PVM_BF_PRIVATE_INVENTORY_DRIFT}
foreach name $names {
  set n [$block findNet $name]
  if {$n eq "NULL" || ![$n isDoNotTouch]} {error "PVM_BF_NET_PROTECTION_DRIFT $pvm_bf_stage $name"}
}
source $::env(PVM_BF_PG_HELPER)
ot_pg_assert_all_native $block [ot_pg_prepare $block]
puts "PVM_BF_STAGE_PASS $pvm_bf_stage graph=exact cells=56000 private_nets=55440 PG=bound"
