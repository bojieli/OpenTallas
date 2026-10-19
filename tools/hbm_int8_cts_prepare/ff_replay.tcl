# Read-only FF placement-RC sensitivity/hold replay of exact emitted CTS ODB.
source /work/kit/libs_FF.tcl
read_db /work/output/cts_only.odb
source $p/setRC.tcl
source /work/kit/constraints.sdc
source /work/kit/vendor/native_pg_binding.tcl
set block [ord::get_db_block]
set mapping [ot_pg_prepare $block]
ot_pg_assert_all_native $block $mapping
set_propagated_clock [all_clocks]
estimate_parasitics -placement
source /work/kit/report_timing.tcl
report_clock_properties [all_clocks]
report_clock_skew
report_checks -path_delay min -format full_clock_expanded -group_path_count 30
report_checks -path_delay max -format full_clock_expanded -group_path_count 30
report_check_types -max_slew -max_capacitance -max_fanout -violators
puts "READONLY_FF_REPLAY_FINISHED NO_DB_WRITE_NO_REPAIR"
