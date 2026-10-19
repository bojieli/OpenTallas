# Read-only actual placed-ODB clock API smoke. No CTS, placement, repair or writes.
if {$::env(INT8_CORNER) ni {TT FF}} {error "BAD_SMOKE_CORNER"}
source /work/kit/libs_$::env(INT8_CORNER).tcl
read_db /work/input/placed.odb
source $p/setRC.tcl
source /work/kit/constraints.sdc
set_propagated_clock [all_clocks]
estimate_parasitics -placement
source /work/kit/report_timing.tcl
set pins [all_registers -clock_pins]
if {[llength $pins] != 2782} {error "SMOKE_WRONG_SINK_COUNT"}
puts "INT8_METRIC_SMOKE_PASS corner=$::env(INT8_CORNER) native_pins=2782 READONLY_NO_CTS_NO_DB_WRITE"
