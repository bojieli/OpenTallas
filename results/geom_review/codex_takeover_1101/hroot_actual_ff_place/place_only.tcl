source $::env(SCRIPTS_DIR)/load.tcl
set hroot_results_dir $::env(RESULTS_DIR)
set ::env(RESULTS_DIR) /work
load_design input.odb input.sdc
set ::env(RESULTS_DIR) $hroot_results_dir
file mkdir $::env(RESULTS_DIR)
set_thread_count 2
set ff_blk [ord::get_db_block]
set ff_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ff_core [$ff_blk getCoreArea]
set ff_x0 [$ff_core xMin];set ff_y0 [$ff_core yMin];set ff_x1 [$ff_core xMax];set ff_y1 [$ff_core yMax]
set ff_rows [$ff_blk getRows];set ff_site [[lindex $ff_rows 0] getSite]
set ff_sw [$ff_site getWidth];set ff_rh [$ff_site getHeight]
set ff_orient {};foreach r $ff_rows {dict set ff_orient [lindex [$r getOrigin] 1] [$r getOrient]}
set oldff {};set cland_avoid_rects {};set nreleased 0
foreach i [$ff_blk getInsts] {
 set n [$i getName];set m [$i getMaster];set mn [$m getName]
 set target [regexp {(^|[/.])u_cland_i_kvpc_Q_N_o_next[/.]} $n]
 if {[regexp {DFF|DHL|DLL|SDF} $mn]} {
  dict set oldff $n [list $i [$i getOrient] [$i getLocation] [$i getPlacementStatus] $target]
 }
 if {$target && ![regexp {DFF|DHL|DLL|SDF} $mn]} {$i setPlacementStatus PLACED;incr nreleased}
 # Existing foreign cland FIRM bodies are real obstacles for this one-band replay.
 if {!$target && ([regexp {DFF|DHL|DLL|SDF} $mn] || ([regexp {(^|[/.])u_cland_} $n] && [$i getPlacementStatus] in {FIRM LOCKED}))} {
  set b [$i getBBox];lappend cland_avoid_rects [list [expr {[$b xMin]/double($ff_dbu)}] [expr {[$b yMin]/double($ff_dbu)}] [expr {[$b xMax]/double($ff_dbu)}] [expr {[$b yMax]/double($ff_dbu)}]]
 }
}
puts "HROOT_PREP release_comb=$nreleased freeze_ff=[dict size $oldff]"
source /work/one_band.tcl
# Freeze all existing FF endpoints through GPL/DPL. Only the reviewed target FF poses change.
set ntarget 0
dict for {n rec} $oldff {
 lassign $rec i ori loc status target
 if {!$target} {$i setOrient $ori;$i setLocation {*}$loc} else {incr ntarget}
 $i setPlacementStatus LOCKED
}
if {$ntarget != 1585} {error "HROOT expected1585 targetFF got$ntarget"}
write_db /work/pre_gp.odb
set ::env(OT_GEOM_OUT) /work/pre_gp.tsv
source /work/geom_dump.tcl
puts HROOT_PRE_GP_READY
flush stdout
# Agent must personally render/look at the actual generated FF layout before GPL.
exec bash -c {for ((q=0;q<1800;q++)); do if [ -f /work/CONTINUE_PLACE ]; then exit 0; fi; sleep 1; done; exit 9}
# Original config has GPL_TIMING_DRIVEN=0, GPL_ROUTABILITY_DRIVEN=0, density=.5.
# No synthesis, clock tree, repair_timing or global_route is called.
global_placement -density 0.5 -skip_io -overflow 0.1
detailed_placement
check_placement -verbose
dict for {n rec} $oldff {
 lassign $rec i ori loc status target
 if {!$target && ([$i getOrient] ne $ori || [$i getLocation] ne $loc)} {error "HROOT unrelated FF moved: $n"}
 if {$target} {$i setPlacementStatus FIRM} else {$i setPlacementStatus $status}
}
write_db /work/3_place.odb
set ::env(OT_GEOM_OUT) /work/geom.tsv
source /work/geom_dump.tcl
puts HROOT_PLACE_ONLY_COMPLETE
