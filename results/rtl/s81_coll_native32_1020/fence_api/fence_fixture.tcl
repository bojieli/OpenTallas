read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*] {read_liberty $f}
read_verilog /work/fence_fixture.v
link_design fence_fixture
initialize_floorplan -die_area {0 0 80 40} -core_area {1 1 79 39} -site asap7sc7p5t
make_tracks M3 -x_offset 0.0 -x_pitch 0.048 -y_offset 0.0 -y_pitch 0.048
set b [ord::get_db_block]
set unit [[ord::get_db_tech] getDbUnitsPerMicron]
source /work/native_cell_fence.tcl
foreach {name box} {left {5 5 20 25} right {60 5 75 25}} {
 set names {}
 for {set j 0} {$j<20} {incr j} {lappend names u_[expr {$j+($name eq "left"?0:20)}]}
 ot_native_cell_fence $name $box $names
}
place_pin -pin_name clk -layer M3 -location {40 0} -pin_size {0.018 0.144} -force_to_die_boundary
place_pin -pin_name d -layer M3 -location {0 20} -pin_size {0.018 0.144} -force_to_die_boundary
place_pin -pin_name q -layer M3 -location {80 20} -pin_size {0.018 0.144} -force_to_die_boundary
create_clock -name clk -period 1 [get_ports clk]
set_wire_rc -signal -layer M3
set_wire_rc -clock -layer M3
global_placement -density 0.3
ot_native_cell_fence_check left {5 5 20 25} GPL
ot_native_cell_fence_check right {60 5 75 25} GPL
puts "NATIVE_FENCE_GPL_PASS groups=2 cells=40"
write_db /work/fence_gpl.odb
# Native birth fixture: two real standard cells appear after GPL, outside both
# regions. Explicit right ownership + single-owner adoption binds them before DP.
foreach name {birth_left birth_right} {
 set i [odb::dbInst_create $b [[ord::get_db] findMaster DFFHQNx1_ASAP7_75t_R] $name]
 $i setLocation [expr {int(40*$unit)}] [expr {int(30*$unit)}]
 $i setPlacementStatus PLACED
}
ot_native_cell_fence_add right {birth_right}
set adopted [ot_native_cell_fence_adopt_unowned left]
if {$adopted!=1} {error "NATIVE_FENCE_BIRTH unexpected count $adopted"}
ot_native_cell_fence_seed_new left {5 5 20 25} {birth_left}
ot_native_cell_fence_seed_new right {60 5 75 25} {birth_right}
detailed_placement
check_placement -verbose
ot_native_cell_fence_check left {5 5 20 25} DP
ot_native_cell_fence_check right {60 5 75 25} DP
puts "NATIVE_FENCE_DP_PASS groups=2 cells=40"
ot_native_cell_band_check {1 1 79 39} FINAL
puts "NATIVE_FENCE_BIRTH_DP_PASS added=2 total=42"
write_db /work/fence_dp.odb
puts "NATIVE_FENCE_GPL_DP_PASS groups=2 cells=40"
