source /src/physical/dsrom_native_relay_20261003/binding.tcl
set aliases [ds_native_binding]
set block [ord::get_db_block]
set expected [concat source_buf {relay_0 relay_1 relay_2 relay_3 relay_4 relay_5 relay_6 relay_7 sink_0 sink_1 sink_2 sink_3 sink_4 sink_5 sink_6 sink_7}]
foreach n $expected {
  set inst [dict get $aliases $n]
  if {$inst == "NULL"} {error "Native clock instance lost: $n"}
  if {[$inst getPlacementStatus] ne "LOCKED"} {error "Native fixed instance moved: $n"}
}
report_clock_skew -setup
report_clock_skew -hold
report_check_types -max_slew -max_capacitance -max_fanout -violators
puts "DS_NATIVE_RELAY_ROUTED_CENSUS_17"
