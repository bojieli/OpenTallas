source /collector/native_pg_binding.tcl
read_db /input/final.odb
set b [ord::get_db_block]
set m [ot_pg_prepare $b]
ot_pg_audit_snapshot $b /output/native_audit.json
set f [open /output/all_native_terms.jsonl {WRONLY CREAT EXCL}]
foreach i [$b getInsts] {
 foreach r [ot_pg_master_census $i] {
  lassign $r mt t why
  set actual ""; set ar ""; set expected ""; set er ""
  if {$why eq "" && [$t getNet] ne "NULL"} {set n [$t getNet]; set actual [$n getName]; set ar [$n getSigType]}
  if {$why eq "" && ![catch {ot_pg_expected $m $i $t} e]} {set expected [$e getName]; set er [$e getSigType]}
  puts $f [ot_pg_json_object [dict create instance [$i getName] master [[$i getMaster] getName] pin [$mt getName] role [$mt getSigType] actual_net $actual actual_role $ar expected_net $expected expected_role $er census_error $why]]
 }
}
close $f
exit
