
set t0 [clock seconds]
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /run/tile.lef
read_def /run/top.def
initialize_floorplan -die_area {0 0 514.080 2246.400} -core_area {0 0 514.080 2246.400} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
set block [ord::get_db_block]
foreach r [$block getRows] { odb::dbRow_destroy $r }
puts "OT_STAT insts=[llength [$block getInsts]]"
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {cl} -voltage_domains {CORE} -pins {M8}
add_pdn_stripe -grid {cl} -layer {M7} -width {0.544} -spacing {4.856} -pitch {10.8} -offset {2.0}
add_pdn_stripe -grid {cl} -layer {M8} -width {2.0} -spacing {6.0} -pitch {16.0} -offset {4.0}
add_pdn_connect -grid {cl} -layers {M7 M8}
define_pdn_grid -macro -cells {w18p_pairtile_4} -halo "0 0 0 0" -voltage_domains {CORE} -name {PairGrid}
add_pdn_connect -grid {PairGrid} -layers {M6 M7}
if {[catch {pdngen} err]} { puts "OT_PDN status=FAIL err=$err" } else {
  set nsw 0; foreach net [$block getNets] { foreach sw [$net getSWires] { incr nsw [llength [$sw getWires]] } }
  puts "OT_PDN status=PASS special_wire_shapes=$nsw" }
puts "OT_TIME pdn_s=[expr {[clock seconds]-$t0}]"
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
set_cmd_units -power W
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_pdnsim_inst_power -inst pair_0_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_0_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_0_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_0_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_1_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_1_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_1_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_1_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_2_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_2_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_2_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_2_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_3_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_3_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_3_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_3_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_4_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_4_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_4_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_4_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_5_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_5_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_5_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_5_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_6_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_6_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_6_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_6_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_7_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_7_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_7_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_7_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_8_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_8_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_8_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_8_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_9_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_9_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_9_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_9_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_10_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_10_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_10_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_10_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_11_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_11_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_11_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_11_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_12_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_12_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_12_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_12_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_13_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_13_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_13_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_13_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_14_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_14_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_14_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_14_t3 -power 0.066575
set_pdnsim_inst_power -inst pair_15_t0 -power 0.066575
set_pdnsim_inst_power -inst pair_15_t1 -power 0.066575
set_pdnsim_inst_power -inst pair_15_t2 -power 0.066575
set_pdnsim_inst_power -inst pair_15_t3 -power 0.066575

proc ot_ir {net src} {
  set_pdnsim_net_voltage -net $net -voltage [expr {$net eq "VDD" ? 0.7 : 0.0}]
  if {[catch {analyze_power_grid -net $net -source_type $src -voltage_file /run/ir_$net.rpt -error_file /run/ir_err_$net.rpt} err]} {
    puts "OT_IR net=$net status=FAIL err=$err"
  } else { puts "OT_IR net=$net status=PASS" }
}
foreach net {VDD VSS} {
  if {[catch {check_power_grid -net $net -error_file /run/pg_err_$net.rpt} err]} { puts "OT_PSM net=$net status=FAIL err=$err" } else { puts "OT_PSM net=$net status=PASS" }
}

ot_ir VDD STRAPS
ot_ir VSS STRAPS
puts "OT_TIME psm_s=[expr {[clock seconds]-$t0}]"
exit
