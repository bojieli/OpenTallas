# Source-only bounded prototype. run.sh requires an exact ROOT approval manifest.
source /work/kit/libs_TT.tcl
read_db /work/input/placed.odb
source $p/setRC.tcl
source /work/kit/vendor/native_pg_binding.tcl
foreach procname {ot_pg_prepare ot_pg_master_census ot_pg_bind_before_protect ot_pg_assert_all_native} {
  if {[llength [info commands $procname]] != 1} {error "missing tested PG adapter $procname"}
}
source /work/kit/constraints.sdc
# ODB stores placement, not the old diagnostic 0.77-clock timing state.
set old {}
set block [ord::get_db_block]
foreach inst [$block getInsts] {
  dict set old [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]
  # Preserve the reviewed ordinary/tie placement; only fresh CTS cells legalize.
  $inst setPlacementStatus FIRM
}
set mapping [ot_pg_prepare $block]
ot_pg_assert_all_native $block $mapping
set pins [all_registers -clock_pins -clock [get_clocks core_clk]]
if {[llength $pins] != 2782} {error "exact INT8 source clock sink mismatch"}
# Fresh tree only, with no timing/data repair. No GRT/route is called here.
clock_tree_synthesis -root_buf BUFx24_ASAP7_75t_R -buf_list {BUFx24_ASAP7_75t_R} -sink_clustering_enable -sink_clustering_size 32
# Bind actual newly created native instances BEFORE any dont-touch protection.
set mapping [ot_pg_prepare $block]
set added 0
foreach inst [$block getInsts] {
  if {![dict exists $old [$inst getName]]} {
    ot_pg_bind_before_protect $mapping $inst
    incr added
  }
}
# Independent complete inventory, not a clock-name filter or only new cells.
set mapping [ot_pg_prepare $block]
ot_pg_assert_all_native $block $mapping
# Only now protect actual graph clock nets, after binding/coverage succeeded.
foreach net [$block getNets] {
  if {[$net getSigType] eq "CLOCK"} {$net setDoNotTouch 1}
}
detailed_placement
check_placement -verbose
foreach inst [$block getInsts] {
  if {[dict exists $old [$inst getName]] && [dict get $old [$inst getName]] ne [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]} {
    error "original placement/master changed: [$inst getName]"
  }
}
set mapping [ot_pg_prepare $block]
ot_pg_assert_all_native $block $mapping
foreach inst [$block getInsts] {
 if {![dict exists $old [$inst getName]]} {$inst setDoNotTouch 1}
}
set_propagated_clock [all_clocks]
estimate_parasitics -placement
# Immutable checkpoint precedes every optional reporting API. Distinct from publication.
set mapping [ot_pg_prepare $block]
ot_pg_assert_all_native $block $mapping
write_db /work/output/cts_checkpoint.odb
write_verilog /work/output/cts_checkpoint.v
set fd [open /work/output/checkpoint.status w]
puts $fd "INT8_PG_CHECKED_CTS_CHECKPOINT_V1 sinks=2782 inserted=$added PG_MASTER_CENSUS_PASS PLACEMENT_IDENTITY_PASS"
close $fd
puts "INT8_PG_CHECKED_CTS_CHECKPOINT_V1 inserted=$added NO_GRT_NO_ROUTE"
source /work/kit/report_timing.tcl
report_clock_properties [all_clocks]
report_clock_skew
report_checks -path_delay max -format full_clock_expanded -group_path_count 30
report_checks -path_delay min -format full_clock_expanded -group_path_count 30
report_check_types -max_slew -max_capacitance -max_fanout -violators
puts "INT8_BOUNDED_CTS_ONLY_FINISHED inserted=$added NO_GRT_NO_ROUTE"
