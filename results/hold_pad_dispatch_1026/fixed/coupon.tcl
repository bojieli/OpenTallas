set root /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $root/lef/asap7_tech_1x_201209.lef
read_lef $root/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach file {asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib} {read_liberty $root/lib/NLDM/$file}
read_verilog /work/coupon.v
link_design coupon
initialize_floorplan -die_area {0 0 20 40} -core_area {1 1 19 39} -site asap7sc7p5t
set block [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
for {set i 0} {$i < 16} {incr i} {
 foreach side {l c} {
  set x [expr {$side eq "l" ? 5 : 7}]
  set inst [$block findInst $side$i]
  $inst setLocation [expr {int($x*$dbu)}] [expr {int((2+2*$i)*$dbu)}]
  $inst setPlacementStatus PLACED
 }
}
source $root/setRC.tcl
create_clock -name launch -period 833 [get_ports la]
create_clock -name capture -period 833 [get_ports ca]
set_clock_latency -source 120 [get_clocks capture]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
estimate_parasitics -placement
set_dont_use [get_lib_cells */*xp*_ASAP7*]
source /work/hold_pad_hb4.tcl
puts "COUPON_BEFORE_HOLD [sta::time_sta_ui [sta::worst_slack_cmd min]]"
repair_timing -setup_margin 0 -hold_margin 5 -repair_tns 100 -skip_last_gasp -max_buffer_percent 100 -verbose
puts "COUPON_AFTER_HOLD [sta::time_sta_ui [sta::worst_slack_cmd min]]"
set n 0
foreach inst [$block getInsts] {if {[[$inst getMaster] getName] eq "HB4xp67_ASAP7_75t_R"} {incr n}}
puts "COUPON_HB4 $n"
write_db /work/repaired.odb
if {$n == 0} {error "HB4 never enabled for default combined repair"}
if {[sta::worst_slack_cmd min] < 0} {error "repair did not close coupon hold"}
puts "COUPON_PASS"
