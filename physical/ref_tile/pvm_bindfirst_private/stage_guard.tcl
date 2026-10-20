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
set report [ot_pg_collect_all_native $block [ot_pg_prepare $block]]
set pending 0
foreach failure [dict get $report failures] {
  set inst [$block findInst [dict get $failure instance]]
  # New ordinary tie births are diagnostic before PDN, never qualification.
  # Protected/fixed/unknown/wrong-role terminals refuse at every stage.
  if {$pvm_bf_stage ni {pre_floorplan post_floorplan pre_macro_place post_macro_place pre_tapcell post_tapcell pre_pdn} ||
      $inst eq "NULL" || [$inst isDoNotTouch] || [$inst getPlacementStatus] in {FIRM LOCKED COVER} ||
      ![regexp {^TIE(HI|LO)x[0-9]+_ASAP7_75t_R$} [[$inst getMaster] getName]] ||
      [dict get $failure reason] ne "OT_PG_FINAL_BINDING" || [dict get $failure actual_net] ne "" ||
      [dict get $failure expected_net] ni {VDD VSS}} {
    error "PVM_BF_STAGE_PG_REFUSED $pvm_bf_stage $failure"
  }
  incr pending
}
set f [open [file join $::env(PVM_BF_RECEIPTS) "$pvm_bf_stage.pg_classification.tcllist"] {WRONLY CREAT EXCL}]
puts $f [list stage $pvm_bf_stage ordinary_new_tie_pg_pending $pending report $report];close $f
if {$pending} {
  puts "PVM_BF_STAGE_GRAPH_PASS $pvm_bf_stage cells=56000 private_nets=55440 protectedPG=bound ordinary_tiePG_pending=$pending NOT_QUALIFIED"
} else {
  ot_pg_assert_all_native $block [ot_pg_prepare $block]
  puts "PVM_BF_STAGE_PASS $pvm_bf_stage cells=56000 private_nets=55440 all_native_PG=bound"
}
