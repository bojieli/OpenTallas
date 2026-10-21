source /proof/native_pg_binding.tcl
source /proof/expect_fail.tcl
read_db [lindex [glob /route/work/orfs/results/asap7/*/base/6_final.odb] 0]
set block [ord::get_db_block]
set picks {}
foreach inst [$block getInsts] {
 if {[$inst findITerm VDD] ne "NULL" && [[$inst findITerm VDD] getNet] eq "NULL"} {lappend picks $inst}
 if {[llength $picks]==2} break
}
foreach rule [$block getGlobalConnects] {odb::dbGlobalConnect_destroy $rule}
foreach n {core_07 io_13 ret_09} {
 set net [odb::dbNet_create $block $n]
 $net setSigType [expr {$n eq "ret_09" ? "GROUND" : "POWER"}]
}
foreach inst $picks rail {core_07 io_13} {
 set region [odb::dbRegion_create $block region_$rail]
 $region addInst $inst
 $inst setDoNotTouch 0
 add_global_connection -net $rail -region region_$rail -inst_pattern .* -pin_pattern {^VDD$} -power
 add_global_connection -net ret_09 -region region_$rail -inst_pattern .* -pin_pattern {^VSS$} -ground
}
foreach inst $picks {
 [$inst findITerm VDD] disconnect
 [$inst findITerm VSS] disconnect
}
set mapping [ot_pg_prepare $block]
foreach inst $picks rail {core_07 io_13} {
 if {[ot_pg_bind_before_protect $mapping $inst]!=2} {error DOMAIN_BIND_COUNT}
 if {[[[$inst findITerm VDD] getNet] getName] ne $rail} {error DOMAIN_SELECTION}
 $inst setDoNotTouch 1
}
puts "DOMAIN_POSITIVE native_two_regions_distinct_declared_supplies arbitrary_names core_07 io_13 ret_09"
set inst [lindex $picks 0]
$inst setDoNotTouch 0
set term [$inst findITerm VDD]
$term connect [$block findNet io_13]
expect_fail wrong_same_role_domain {ot_pg_bind_before_protect $mapping $inst} {*OT_PG_WRONG_DOMAIN*}
expect_fail all_native_no_exemption {ot_pg_assert_all_native $block $mapping} {*OT_PG_FINAL_FAIL*}
add_global_connection -net core_07 -inst_pattern .* -pin_pattern {^VDD$} -power
expect_fail conflicting_region_global {ot_pg_prepare $block} {*OT_PG_AMBIGUOUS_DOMAIN*}
add_global_connection -net core_07 -inst_pattern .* -pin_pattern {^VDD.*$} -power
expect_fail unsupported_pin_regex {ot_pg_prepare $block} {*OT_PG_UNSUPPORTED_PIN_PATTERN*}
puts DOMAIN_PROBE_PASS
exit
