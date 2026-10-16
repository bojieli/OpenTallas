read_lef tech.lef
read_lef -library /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef -library hbm.lef
read_verilog fixture.v
link_design fixture
# Actual KV die outlines/homes and orientations; no synthetic shrink.
initialize_floorplan -die_area {0 0 10798.272 24587.280} -core_area {0 0 10798.272 24587.280} -site asap7sc7p5t
set block [ord::get_db_block]
foreach {name orient x y} {phy_WS MY 20.304 222.480 phy_WN MY 20.304 12365.976 phy_ES R0 9944.208 222.480 phy_EN R0 9944.208 12365.976} {
 set inst [$block findInst $name];$inst setOrient $orient;$inst setLocation [expr {round($x*1000)}] [expr {round($y*1000)}];$inst setPlacementStatus FIRM
}
source hbm_pg_interface.tcl
ot_hbm_pg::check
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core -voltage_domains CORE -pins M9
# Actual KV M8 pitch/width/phase. Sparse M9 is a fixture supply trunk only.
add_pdn_stripe -grid core -layer M8 -width .48 -pitch 10.88 -offset 2
add_pdn_stripe -grid core -layer M9 -width .48 -pitch 200 -offset 2
add_pdn_connect -grid core -layers {M8 M9}
define_pdn_grid -macro -cells {qkd_hbm3e_phy_pc} -voltage_domains CORE -name phy -halo {0 0 0 0}
add_pdn_stripe -grid phy -layer M5 -width .12 -pitch 10.88 -offset 1
add_pdn_connect -grid phy -layers {M4 M5}
add_pdn_connect -grid phy -layers {M5 M8}
pdngen -failed_via_report failed_vias.rpt
check_power_grid -net VDD
check_power_grid -net VSS
write_db fixture.odb
puts HBM_PHY_DECLARED_POWER_FIXTURE_PASS
