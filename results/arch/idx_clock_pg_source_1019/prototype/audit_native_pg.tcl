# Read-only audit: OT_PG_AUDIT_ODB=... OT_PG_AUDIT_REPORT=... openroad -exit audit_native_pg.tcl
source [file join [file dirname [info script]] native_pg_binding.tcl]
if {![info exists ::env(OT_PG_AUDIT_ODB)] || ![info exists ::env(OT_PG_AUDIT_REPORT)]} {error "set OT_PG_AUDIT_ODB and OT_PG_AUDIT_REPORT"}
set odb_path $::env(OT_PG_AUDIT_ODB)
set report_path $::env(OT_PG_AUDIT_REPORT)
read_db $odb_path
set block [ord::get_db_block]
set receipt [dict create input_odb $odb_path block [$block getName]]
set out [open $report_path w]
if {[catch {ot_pg_prepare $block} mapping]} {
  dict set receipt status REFUSED; dict set receipt reason $mapping
  puts $out $receipt; close $out
  puts "NATIVE_PG_AUDIT_REFUSED $mapping"; exit 1
}
set report [ot_pg_collect_all_native $block $mapping]
set status [expr {[dict get $report failure_count] ? "FAIL" : "PASS"}]
dict set receipt status $status; dict set receipt native_pg $report
set rules {}
foreach rule [$block getGlobalConnects] {
  set region [$rule getRegion]
  set region_name ""; if {$region ne "NULL"} {set region_name [$region getName]}
  set net [$rule getNet]
  lappend rules [dict create inst_pattern [$rule getInstPattern] pin_pattern [$rule getPinPattern] net [$net getName] role [$net getSigType] region $region_name]
}
dict set receipt declared_native_rules $rules
puts $out $receipt; close $out
puts "NATIVE_PG_AUDIT_$status checked=[dict get $report checked] failures=[dict get $report failure_count]"
if {$status eq "FAIL"} {exit 2}
exit 0
