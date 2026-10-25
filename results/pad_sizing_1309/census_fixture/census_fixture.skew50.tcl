read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /out/libs/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_verilog /out/census_fixture.v
link_design census_fixture
create_clock -name clk -period 833 [get_ports clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_clock_transition 10 [get_clocks clk]
set_clock_latency 50 [get_pins capture/CLK]
source /out/census_clock_family.tcl
report_checks -path_delay min -format full_clock_expanded -digits 5
set m [ot_cf_output_hold_census]
puts "CENSUS_REAL $m"
if {[dict get $m n] < 1 || [dict get $m worst_ps] >= 0 || [dict get $m tns_ps] >= 0} {error "negative real path not exercised"}
rename get_property census_native_get_property
set ::bad_metric NaN
proc get_property {object property args} {
 if {$property eq "slack"} {return $::bad_metric}
 return [census_native_get_property $object $property {*}$args]
}
foreach bad {NaN {} unavailable} {
 set ::bad_metric $bad
 set failed [catch {ot_cf_output_hold_census} msg]
 puts "CENSUS_BAD_METRIC value=<$bad> rejected=$failed message=<$msg>"
 if {!$failed || ![string match {*census unavailable*} $msg]} {error "malformed metric not rejected"}
}
rename get_property {}
rename census_native_get_property get_property
puts "CENSUS_FIXTURE_PASS"
