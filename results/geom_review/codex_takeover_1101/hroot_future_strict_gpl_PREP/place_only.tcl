error "HROOT_CHUNK_STRICT_CANDIDATE_NOT_DISPATCHABLE_ROOT_ADOPTION_SCOPE_AND_LOOK_REQUIRED"
# PREP ONLY. Root authorization and approved PG helper/input are required before dispatch.
source $::env(SCRIPTS_DIR)/load.tcl
set saved_results $::env(RESULTS_DIR)
set ::env(RESULTS_DIR) /work
load_design input.odb input.sdc
set ::env(RESULTS_DIR) $saved_results
file mkdir $::env(RESULTS_DIR)
set_thread_count 2
source /work/native_pg_binding.tcl
set b [ord::get_db_block]
set fh [open /work/pg_pre.json {WRONLY CREAT EXCL}]
set pg [ot_pg_write_snapshot $b $fh]
if {[dict get $pg failure_count] != 0} {error "HROOT_GUIDE_PG_INPUT_NOT_CLOSED"}
source /work/strict_eval.tcl
foreach mode {GPL_TIMING_DRIVEN GPL_ROUTABILITY_DRIVEN} {
 if {![info exists ::env($mode)] || $::env($mode) ne "0"} {error "HROOT_STRICT_PREP_EXACT_MODE_ZERO_REQUIRED $mode"}
}
set hroot_eval [ot_pg_candidate_strict_place_eval /work/nativepgbirth.so {
source /work/chunk_guide_spec_PREP.tcl
set selected [dict create]
foreach {group prefixes x0 y0 x1 y1} $::ot_mrg_spec {
 foreach name $prefixes {
  if {[dict exists $selected $name]} {error "HROOT_GUIDE_DUPLICATE $name"}
  dict set selected $name $group
 }
}
if {[dict size $selected] != 4609} {error "HROOT_GUIDE_EXPECTED4609"}
set saved [dict create];set mobile 0
foreach inst [$b getInsts] {
 set n [$inst getName];set clean [string map {"\\" ""} $n]
 set master [[$inst getMaster] getName]
 dict set saved $n [list $inst [$inst getOrient] [$inst getLocation] [$inst getPlacementStatus]]
 if {[dict exists $selected $clean]} {
  if {[regexp {DFF|DHL|DLL|SDF} $master]} {error "HROOT_GUIDE_SELECTED_FF $n"}
  $inst setPlacementStatus PLACED
  incr mobile
 } else {
  $inst setPlacementStatus LOCKED
 }
}
if {$mobile != 4609} {error "HROOT_GUIDE_NATIVE_MEMBER_COUNT $mobile"}
source /work/macro_reg_guide.tcl
write_db /work/pre_gp.odb
set ::env(OT_GEOM_OUT) /work/pre_gp.tsv
source /work/geom_dump.tcl
puts HROOT_CHUNK_ACTUAL_PRE_GP_READY
flush stdout
# A native geometry LOOK is mandatory before this sole producer begins GPL.
exec bash -c {for ((q=0;q<1800;q++)); do if [ -f /work/CONTINUE_PLACE ]; then exit 0; fi; sleep 1; done; exit 9}
global_placement -density 0.5 -skip_io -overflow 0.1
source /work/macro_reg_guide_release.tcl
detailed_placement
check_placement -verbose
dict for {n rec} $saved {
 lassign $rec inst orient loc status
 set clean [string map {"\\" ""} $n]
 if {![dict exists $selected $clean] && ([$inst getOrient] ne $orient || [$inst getLocation] ne $loc)} {error "HROOT_GUIDE_PROTECTED_POSE $n"}
 $inst setPlacementStatus $status
}
set fh [open /work/pg_post.json {WRONLY CREAT EXCL}]
set pg [ot_pg_write_snapshot $b $fh]
if {[dict get $pg failure_count] != 0} {error "HROOT_GUIDE_PG_POST_NOT_CLOSED"}
}]
foreach field {creates swaps bound} {
 if {[dict get $hroot_eval native $field] != 0} {error "HROOT_STRICT_PREP_UNEXPECTED_NATIVE_BIRTH $hroot_eval"}
}
# Strict whole-body cleanup succeeded, callback inactive, zero native birth/swap/bind.
# Independent full pose/source/graph guard and final saved PG audit still required.
write_db /work/3_place.odb
set ::env(OT_GEOM_OUT) /work/geom.tsv
source /work/geom_dump.tcl
puts HROOT_CHUNK_DB_WRITTEN_FULL_GUARD_AND_LOOK_PENDING
