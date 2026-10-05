# Read-only export; output is an analytical witness, never fed into a flow.
read_db /inputs/5_1_grt.odb
puts "EXPORT|COMMANDS|[info commands *lef*]"
set tech [ord::get_db_tech]
foreach ln {M4 M5 V4} {
 set l [$tech findLayer $ln]
 foreach getter {getTechLayerSpacingEolRules getTechLayerCutEnclosureRules getTechLayerCutSpacingTableDefRules getV54SpacingRules} {
  set i 0
  foreach r [$l $getter] {
   if {[catch {$r __audit_methods__} msg]} {puts "EXPORT|METHODS|$ln|$getter|$i|$msg"}
   incr i
  }
 }
}
if {[llength [info commands write_tech_lef]]} {
 write_tech_lef /outputs/actual_db_tech.lef
 puts "EXPORT|TECH_LEF|COMPLETE"
}
puts "EXPORT|COMPLETE"
exit
