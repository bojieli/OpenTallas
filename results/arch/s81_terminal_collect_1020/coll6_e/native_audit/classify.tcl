set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $P/lib/NLDM/*RVT*TT*.lib*] {read_liberty $l}
foreach l [glob /src/physical/asap7_memory_macros_v2/*/*_tt.lib] {read_liberty $l}
read_db /case/routes/gate/work/orfs/results/asap7/opentallas_dsfd_coll_lane_e_safe4_asap7_ref_gate/base/5_1_grt.odb
set b [ord::get_db_block]
set f [open /audit/master_pins.tsv w]
set seen [dict create]
foreach i [$b getInsts] {
 set m [$i getMaster];set n [$m getName]
 if {[dict exists $seen $n]} continue
 dict set seen $n 1
 foreach p [$m getMTerms] {puts $f [join [list $n [$m getType] [$p getName] [$p getSigType] [$p getIoType]] "\t"]}
}
close $f
puts "MASTER_PIN_TYPES_DUMP_PASS [dict size $seen]"
set f [open /audit/unconnected_outputs.tsv w]
foreach i [$b getInsts] {
 foreach p [$i getITerms] {
  if {[$p getIoType] eq "OUTPUT" && [[$p getMTerm] getSigType] eq "SIGNAL" && [$p getNet] eq "NULL"} {puts $f [join [list [string map {\\ {}} [$i getName]] [[$i getMaster] getName] [[$p getMTerm] getName]] "\t"]}
 }
}
close $f

source /src/physical/common_flow/native_pg_binding.tcl
ot_pg_audit_snapshot $b /audit/grt_native_pg_snapshot.json
