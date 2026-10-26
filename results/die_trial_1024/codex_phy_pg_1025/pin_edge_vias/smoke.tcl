read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/pg_mixed.lef
read_verilog /work/smoke.v
link_design pin_smoke
initialize_floorplan -die_area {0 0 345.6 345.6} -core_area {0 0 345.6 345.6} -site asap7sc7p5t
set i [[ord::get_db_block] findInst mixed]
$i setLocation 0 0
$i setPlacementStatus FIRM
source /work/pdn.tcl
pdngen
ot_pg_connect_pins
source /work/pg_short_check.tcl
source /work/bumps.tcl
foreach n {VDD VDDPHY VSS} { check_power_grid -net $n; puts "OT_PG_CHECK_OK $n" }
write_db /work/pin_smoke.odb
puts OT_DONE
