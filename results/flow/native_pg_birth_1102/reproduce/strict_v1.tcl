# Native PG callback mechanism test on an isolated copy, never a sign-off run.
set p /OpenROAD-flow-scripts/flow/platforms/asap7
foreach pattern {AO_RVT_TT_nldm_211120.lib.gz INVBUF_RVT_TT_nldm_220122.lib.gz OA_RVT_TT_nldm_211120.lib.gz SEQ_RVT_TT_nldm_220123.lib SIMPLE_RVT_TT_nldm_211120.lib.gz} {
  read_liberty $p/lib/NLDM/asap7sc7p5t_$pattern
}
read_db /work/input.odb
read_sdc /work/constraint.sdc
source $p/setRC.tcl
source /work/v1/native_pg_binding.tcl
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
set suffix strict_v1
set ::env(OT_PG_STRICT) 1
ot_pg_install_unsupported_birth_guards
if {![catch {repair_design} missing] || ![string match *CAPABILITY_REQUIRED* $missing]} {error PG_GUARD_DEFAULT_CHANGED}
proc ot_native_pg_status {} {return {contract native_pg_birth.flat_literal.v1 active 1 database_id 1 block_id 1}}
proc ot_native_pg_audit {} {return {fake 1}}
if {![catch {repair_design} fake] || ![string match *CAPABILITY_REQUIRED* $fake]} {error PG_GUARD_ACCEPTED_FAKE_TCL_CAPABILITY}
rename ot_native_pg_status {};rename ot_native_pg_audit {}
ot_pg_native_birth_eval /work/v1/build/nativepgbirth.so {
  set_max_fanout 8 [current_design]
  repair_design -max_wire_length 20 -max_utilization 90
  puts "PG_NATIVE_REAL_REPAIR [ot_native_pg_audit]"
  if {![catch {clock_tree_synthesis} other] || ![string match *CAPABILITY_REQUIRED* $other]} {error PG_GUARD_ADMITTED_UNVALIDATED_COMMAND}
  set after_count [llength [$b getInsts]]
  puts "PG_NATIVE_REAL_COUNTS before=$before_count after=$after_count"
  if {$after_count <= $before_count} {error PG_NATIVE_NO_BIRTHS}
  # Source-owned RC command follows the actual native resizer transaction.
  estimate_parasitics -placement
  set f [open /work/repair_${suffix}_topology.tcl {WRONLY CREAT EXCL}];puts $f [snapshot $b];close $f
  ot_pg_audit_snapshot $b /work/repair_${suffix}_audit.json
  write_db /work/repair_${suffix}.odb
}
if {[dict get [ot_native_pg_status] active]} {error PG_GUARD_NOT_UNINSTALLED}
if {![catch {repair_design} inactive] || ![string match *CAPABILITY_REQUIRED* $inactive]} {error PG_GUARD_INACTIVE_CHANGED}
set before_reload [snapshot $b]
if {![catch {ot_pg_native_birth_eval /work/v1/build/nativepgbirth.so {read_db /work/input.odb}} reload] || ![string match *CONTEXT_FROZEN* $reload]} {error PG_GUARD_ALLOWED_RELOAD}
if {[dict get [ot_native_pg_status] active] || $before_reload ne [snapshot $b]} {error PG_GUARD_RELOAD_CLEANUP_CHANGED}
puts NATIVE_PG_STRICT_V1_AND_CONTEXT_CLEANUP_PASS
puts "PG_NATIVE_REAL_REPAIR_DONE $suffix"
