# Source-only bounded prototype. run.sh requires an exact ROOT approval manifest.
set p /OpenROAD-flow-scripts/flow/platforms/asap7
foreach lib [glob $p/lib/NLDM/*RVT_TT*.lib*] {read_liberty $lib}
read_db /work/input/placed.odb
source $p/setRC.tcl
source /work/prototype/pg_adapter.tcl
foreach procname {ot_pg_bind_before_protect ot_pg_assert_all_native} {
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
ot_pg_assert_all_native $block
set pins [all_registers -clock_pins -clock [get_clocks core_clk]]
if {[llength $pins] != 2782} {error "exact INT8 source clock sink mismatch"}
# Fresh tree only, with no timing/data repair. No GRT/route is called here.
clock_tree_synthesis -root_buf BUFx24_ASAP7_75t_R -buf_list {BUFx24_ASAP7_75t_R} -sink_clustering_enable -sink_clustering_size 32
# Bind actual newly created native instances BEFORE any dont-touch protection.
set added 0
foreach inst [$block getInsts] {
  if {![dict exists $old [$inst getName]]} {
    ot_pg_bind_before_protect $inst
    incr added
  }
}
# Independent complete inventory, not a clock-name filter or only new cells.
ot_pg_assert_all_native $block
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
ot_pg_assert_all_native $block
set_propagated_clock [all_clocks]
estimate_parasitics -placement
report_clock_properties [all_clocks]
report_clock_skew
report_checks -path_delay max -format full_clock_expanded -group_path_count 30
report_checks -path_delay min -format full_clock_expanded -group_path_count 30
report_check_types -max_slew -max_capacitance -max_fanout -violators
write_db /work/output/cts_only.odb
write_verilog /work/output/cts_only.v
puts "INT8_BOUNDED_CTS_ONLY_FINISHED inserted=$added NO_GRT_NO_ROUTE"
