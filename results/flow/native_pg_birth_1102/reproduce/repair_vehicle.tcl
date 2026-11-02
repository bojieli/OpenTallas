# Native PG callback mechanism test on an isolated copy, never a sign-off run.
set p /OpenROAD-flow-scripts/flow/platforms/asap7
foreach pattern {AO_RVT_TT_nldm_211120.lib.gz INVBUF_RVT_TT_nldm_220122.lib.gz OA_RVT_TT_nldm_211120.lib.gz SEQ_RVT_TT_nldm_220123.lib SIMPLE_RVT_TT_nldm_211120.lib.gz} {
  read_liberty $p/lib/NLDM/asap7sc7p5t_$pattern
}
read_db /work/input.odb
read_sdc /work/constraint.sdc
source $p/setRC.tcl
source /work/native_pg_binding.tcl
set b [ord::get_db_block]
ot_pg_assert_all_native $b [ot_pg_prepare $b]
proc snapshot {b} {
  set rows {}
  foreach i [$b getInsts] {
    set terms {}
    foreach t [$i getITerms] {
      if {[[$t getMTerm] getSigType] in {POWER GROUND}} continue
      set n [$t getNet]; set name NULL; if {$n ne "NULL"} {set name [$n getName]}
      lappend terms [list [[$t getMTerm] getName] $name]
    }
    lappend rows [list [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient] [$i getPlacementStatus] [$i isDoNotTouch] [$i getSourceType] [lsort $terms]]
  }
  set nets {}; foreach n [$b getNets] {lappend nets [list [$n getName] [$n getSigType] [$n isSpecial] [$n isDoNotTouch]]}
  return [list [lsort $rows] [lsort $nets]]
}
estimate_parasitics -placement
set before_count [llength [$b getInsts]]
set suffix $::env(PG_CASE)
if {$suffix eq "callback"} {
  load /work/nativepgbirth.so Nativepgbirth
  set db [$b getDataBase]
  ot_native_pg_install [$db getId] [$b getId]
}
try {
  set_max_fanout 8 [current_design]
  repair_design -max_wire_length 20 -max_utilization 90
  if {$suffix eq "callback"} {puts "PG_NATIVE_REAL_REPAIR [ot_native_pg_audit]"}
  set after_count [llength [$b getInsts]]
  puts "PG_NATIVE_REAL_COUNTS before=$before_count after=$after_count"
  if {$after_count <= $before_count} {error PG_NATIVE_NO_BIRTHS}
  # Source-owned RC command follows the actual native resizer transaction.
  estimate_parasitics -placement
  set f [open /work/repair_${suffix}_topology.tcl {WRONLY CREAT EXCL}];puts $f [snapshot $b];close $f
  ot_pg_audit_snapshot $b /work/repair_${suffix}_audit.json
  write_db /work/repair_${suffix}.odb
} finally {
  if {$suffix eq "callback"} {ot_native_pg_uninstall}
}
puts "PG_NATIVE_REAL_REPAIR_DONE $suffix"
