read_lef tech.lef
read_lef -library /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef -library serdes.lef
read_lef -library ucie.lef
read_verilog fixture.v
link_design fixture
initialize_floorplan -die_area {0 0 7000 9000} -core_area {10 10 6990 8990} -site asap7sc7p5t
set block [ord::get_db_block]
foreach {name orient x y} {serdes_r0 R0 100 100 ucie_mx MX 3000 100 serdes_my MY 100 2200 ucie_r180 R180 3000 2200 serdes_mx MX 100 4400 ucie_r0 R0 3000 4400 serdes_r180 R180 100 6600 ucie_my MY 3000 6600} {
  set i [$block findInst $name]; $i setOrient $orient; $i setLocation [expr {$x*1000}] [expr {$y*1000}]; $i setPlacementStatus FIRM
}
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core -voltage_domains CORE -pins {M9} -starts_with GROUND
add_pdn_stripe -grid core -layer M8 -width .48 -pitch 20 -offset 0
add_pdn_stripe -grid core -layer M9 -width .48 -pitch 200 -offset 0
add_pdn_connect -grid core -layers {M8 M9}
source assumed_access.tcl
ot_assumed_phy_pg_grids
source pdn_bbox_obs.tcl
ot_pdn_bbox::begin /work
try {pdngen -failed_via_report failed_vias.rpt} finally {ot_pdn_bbox::restore}
check_power_grid -net VDD
check_power_grid -net VSS
write_db fixture.odb
puts PHY_PG_FIXTURE_PASS
