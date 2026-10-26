read_lef tech.lef
read_lef -library /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef -library master.lef
read_lef -library tap.lef
set db [ord::get_db]
read_verilog fixture.v
link_design fixture
set block [ord::get_db_block]
initialize_floorplan -die_area {0 0 4000 4000} -core_area {10 10 3990 3990} -site asap7sc7p5t
set inst [$block findInst ctl]
$inst setLocation 100000 100000
$inst setPlacementStatus FIRM
source pdn_bbox_obs.tcl
set tap [$block findInst tap]
$tap setLocation 1000000 1000000
$tap setPlacementStatus FIRM
set tap_master [$tap getMaster]
set before_obs [ot_pdn_bbox::obstructions $tap_master]
ot_pdn_bbox::begin [pwd]
puts "TAP_OBS_REDUCTION [llength $before_obs] -> [llength [[$tap getMaster] getObstructions]]"
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core -voltage_domains CORE -pins {M9} -starts_with GROUND
add_pdn_stripe -grid core -layer M8 -width .48 -pitch 200 -offset 0
add_pdn_stripe -grid core -layer M9 -width .48 -pitch 200 -offset 0
add_pdn_connect -grid core -layers {M8 M9}
define_pdn_grid -macro -instances {^ctl$} -voltage_domains CORE -name macro -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid macro -layer M8 -width .48 -pitch 200 -offset 100
add_pdn_connect -grid macro -layers {M7 M8}
add_pdn_connect -grid macro -layers {M8 M9}
define_pdn_grid -macro -instances {^tap$} -voltage_domains CORE -name tapgrid -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid tapgrid -layer M6 -width .16 -pitch 20 -offset 0
add_pdn_stripe -grid tapgrid -layer M7 -width .16 -pitch 20 -offset 0
add_pdn_connect -grid tapgrid -layers {M5 M6}
add_pdn_connect -grid tapgrid -layers {M6 M7}
add_pdn_connect -grid tapgrid -layers {M7 M8}
pdngen
set layer [[[ord::get_db] getTech] findLayer M1]
odb::dbBox_create $tap_master $layer 1 1 2 2
ot_pdn_bbox::restore
if {$before_obs ne [ot_pdn_bbox::obstructions [$tap getMaster]]} {error "TAP OBS changed"}
check_power_grid -net VDD
check_power_grid -net VSS
write_db roundtrip.odb
set out [open expected_obs.txt w]; puts $out $before_obs; close $out
puts FIXTURE_PASS
