set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $plat/lib/NLDM/*INVBUF*RVT_TT*] {read_liberty $l}
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog /test/lifecycle_api.v
link_design lifecycle_api
create_clock -name core_clk -period 833 [get_ports ck]
set block [ord::get_db_block]
foreach name {u_ck_a u_ck_b} {
 set inst [$block findInst $name]
 $inst setLocation 10000 10000
 $inst setPlacementStatus PLACED
 set_dont_touch [get_cells $name]
}
remove_buffers
foreach name {u_ck_a u_ck_b} {
 if {[$block findInst $name] eq "NULL"} {error "Root removed despite exact protection"}
}
puts "ROOT_KEEP_REMOVE_BUFFERS PASS cells=2"
source /test/clock_spine.tcl
set ::ot_sp_internal_roots [dict create ga {u_ck_a/Y BUFx24_ASAP7_75t_R A ck} gb {u_ck_b/Y BUFx24_ASAP7_75t_R A ck}]
rename ot_clock_spines tx_test_unused_physical_builder
set fixture_fail 0
proc ot_clock_spines {} {
 global fixture_fail
 set block [ord::get_db_block]
 foreach name {u_ck_a u_ck_b} {
  set inst [$block findInst $name]
  if {[$inst isDoNotTouch]} {error "Root was not released: $name"}
  set pin [$inst findITerm A]; set net [$pin getNet]
  $pin disconnect; $pin connect $net
 }
 if {$fixture_fail} {error "EXPECTED_BUILD_FAILURE"}
 return 1
}
source /test/preserve_branches_cts.tcl
proc check_restored {} {
 foreach name {u_ck_a u_ck_b} {
  if {![[[ord::get_db_block] findInst $name] isDoNotTouch]} {error "Root protection not restored: $name"}
 }
}
if {[ot_clock_spines] != 1} {error "Successful builder return lost"}
check_restored
puts "ROOT_LIFECYCLE_SUCCESS PASS"
set fixture_fail 1
if {![catch {ot_clock_spines} msg] || $msg ne "EXPECTED_BUILD_FAILURE"} {error "Construction error was not retained: $msg"}
check_restored
puts "ROOT_LIFECYCLE_FAILURE_RESTORE PASS"
set inst [$block findInst u_ck_a]
$inst setDoNotTouch 0
if {![catch {ot_clock_spines} msg] || ![string match {*POST_SYNTH protection missing*} $msg]} {error "Missing protection accepted: $msg"}
$inst setDoNotTouch 1
check_restored
puts "ROOT_LIFECYCLE_MISSING_PROTECTION CAUGHT"
set net [[$inst findITerm Y] getNet]
$net setDoNotTouch 1
if {![catch {ot_clock_spines} msg] || ![string match {*output net protected*} $msg]} {error "Preprotected net accepted: $msg"}
$net setDoNotTouch 0
check_restored
puts "ROOT_LIFECYCLE_PREPROTECTED_NET CAUGHT"
puts "ROOT_LIFECYCLE_API PASS remove_buffers/success/failure_restore/two_causals"
exit
