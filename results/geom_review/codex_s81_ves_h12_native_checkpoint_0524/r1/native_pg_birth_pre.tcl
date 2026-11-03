source /work/native_pg_binding.tcl
if {![ot_pg_strict_enabled]} {error VES_GRT_REQUIRES_STRICT}
ot_pg_native_birth_begin /work/nativepgbirth.so
# Exact deletion guard runs immediately, before original PRE/any analysis.
set vb [ord::get_db_block]
set before_inst [dict create]; set old_spacers [dict create]; set checked_masters [dict create]
set sf [open /work/PG_ONLY_SPACERS.tsv {WRONLY CREAT EXCL}]
foreach inst [$vb getInsts] {
 set name [$inst getName]; set master [$inst getMaster]
 set record [list [$inst getId] [$master getId] [$master getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] [$inst isDoNotTouch]]
 dict set before_inst $name $record
 if {[$master getType] ne "CORE_SPACER"} continue
 if {![dict exists $checked_masters [$master getId]]} {
  set terms [$master getMTerms]
  if {![llength $terms]} {error "VES_SPACER_WITHOUT_PG_TERMS [$master getName]"}
  foreach mt $terms {if {[$mt getSigType] ni {POWER GROUND}} {error "VES_SIGNAL_SPACER_FORBIDDEN [$master getName]"}}
  dict set checked_masters [$master getId] 1
 }
 dict set old_spacers $name $record
 puts $sf [list SPACER $name {*}$record]
}
close $sf
remove_fillers
set after_inst [dict create]
foreach inst [$vb getInsts] {
 set name [$inst getName]; set master [$inst getMaster]
 if {![dict exists $before_inst $name] || [dict exists $old_spacers $name]} {error "VES_SPACER_DELETE_UNEXPECTED_SURVIVOR_OR_BIRTH $name"}
 set record [list [$inst getId] [$master getId] [$master getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] [$inst isDoNotTouch]]
 if {$record ne [dict get $before_inst $name]} {error "VES_SPACER_DELETE_CHANGED_NONSPACER $name"}
 dict set after_inst $name 1
}
set observed_deleted {}
dict for {name record} $before_inst {if {![dict exists $after_inst $name]} {lappend observed_deleted $name}}
if {[lsort $observed_deleted] ne [lsort [dict keys $old_spacers]]} {error VES_SPACER_DELETE_SET_MISMATCH}
set sf [open /work/PG_ONLY_SPACERS.deleted_names.txt {WRONLY CREAT EXCL}]
foreach name [lsort $observed_deleted] {puts $sf $name}
close $sf
set removal_birth_audit [ot_native_pg_audit]
if {[dict get $removal_birth_audit creates] != 0 || [dict get $removal_birth_audit swaps] != 0} {error VES_SPACER_REMOVAL_CREATED_OR_SWAPPED_CELLS}
set sf [open /work/SPACER_DELETE_GUARD.json {WRONLY CREAT EXCL}]
puts $sf [format {{"before_instances":%d,"expected_PG_only_spacers":%d,"observed_deleted":%d,"surviving_nonspacers":%d,"deleted_set_exact":true,"surviving_master_pose_orient_status_DNT_exact":true,"before_analysis":true,"native_creates":0,"native_swaps":0}} [dict size $before_inst] [dict size $old_spacers] [llength $observed_deleted] [dict size $after_inst]]
close $sf
unset before_inst after_inst old_spacers observed_deleted
puts "VES_SPACER_DELETE_GUARD PASS: exact PG-only set; all surviving instance/master/pose/orient/status/DNT records intact before analysis"
source /work/clk_freeze.tcl
# Source-frozen geometry before any original PRE or native optimization.
ot_clk_dump $::env(RESULTS_DIR)/source_wire_pre.tsv routed_source /work/reset_nets.txt
source /work/grt_pre_core.tcl
