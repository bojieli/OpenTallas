# S81-DIE7 REAL-VIEW die case (tools/s81_dv/dv_rvcase.py) -- census in case.json (stand-ins labelled)
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob /work/views/*.lef] { read_lef $f }
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
foreach f [glob /work/views/*.lib] { read_liberty $f }
read_verilog /work/die.v
link_design dv_die
initialize_floorplan -die_area {0 0 31968.500 25000.000} -core_area {1.080 1.080 31967.420 24998.920} -site asap7sc7p5t
make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064
make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048
make_tracks M3 -x_offset 0.009 -x_pitch 0.640 -y_offset 0.009 -y_pitch 0.640
make_tracks M2 -x_offset 0.009 -x_pitch 0.640 -y_offset 0.045 -y_pitch 0.640
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
set p0 [clock seconds]
source /work/place.tcl
puts "OT_PLACE_S [expr {[clock seconds]-$p0}] insts [llength [get_cells *]]"
set ot_blk [ord::get_db_block]; set ot_core [$ot_blk getCoreArea]
set ot_gsites [expr {double([$ot_core dx]) * [$ot_core dy] / (0.27 * 0.054 * pow([$ot_blk getDbUnitsPerMicron], 2)) / 1e9}]
if {$ot_gsites > 2.0} {
  puts "OT_CLUSTER_LEGAL_MODE snap gsites=[format %.2f $ot_gsites]"
  if {![llength [info procs ot_cluster_snap_legalize]]} { source /work/cluster_bounds.tcl }
  if {[ot_cluster_snap_legalize /work/out/snap_legalize_place.json] != 0} { puts "OT_CLUSTER_SNAP_FAIL place"; exit 4 }
} else {
  puts "OT_CLUSTER_LEGAL_MODE dpl gsites=[format %.2f $ot_gsites]"
  if {![info exists ::ot_cluster_macro_blk]} {
    set ::ot_cluster_macro_blk 0
    set dbu [$ot_blk getDbUnitsPerMicron]
    set cx [$ot_core xMin]; set cy [$ot_core yMin]
    set rh [expr {round(0.27 * $dbu)}]; set sw [expr {round(0.054 * $dbu)}]
    foreach inst [$ot_blk getInsts] {
      if {![[$inst getMaster] isBlock]} { continue }
      set bb [$inst getBBox]
      set x0 [expr {$cx + int(floor(double([$bb xMin] - $cx) / $sw)) * $sw}]
      set y0 [expr {$cy + int(floor(double([$bb yMin] - $cy) / $rh)) * $rh}]
      set x1 [expr {$cx + int(ceil(double([$bb xMax] - $cx) / $sw)) * $sw}]
      set y1 [expr {$cy + int(ceil(double([$bb yMax] - $cy) / $rh)) * $rh}]
      odb::dbBlockage_create $ot_blk $x0 $y0 $x1 $y1
      incr ::ot_cluster_macro_blk
    }
    puts "OT_CLUSTER_MACRO_BLOCKAGES $::ot_cluster_macro_blk"
  }
  if {[catch {detailed_placement} e]} { puts "OT_CLUSTER_DPL_FAIL place $e"; exit 4 }
  if {[catch {check_placement -verbose -report_file /work/out/check_placement_place.rpt} e]} { puts "OT_CLUSTER_CHECK_PLACEMENT_FAIL place $e"; exit 4 }
}
puts "OT_CLUSTER_LEGAL place"

source /work/die_repeaters.tcl
source /work/tie_place.tcl
if {[ot_rv_place_ties /work/out/tie_spread.json] != 0} { puts "OT_TIE_PLACE_FAIL"; exit 4 }
write_db /work/out/place.odb
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_wire_rc -signal -layer M6
# top-port nets (regional clock roots, rst_n, PMA, land_fault): special = not die-top routing (DIE-CLOCK roots ideal here)
set nsp 0
foreach bt [[ord::get_db_block] getBTerms] { set n [$bt getNet]; if {$n ne "NULL"} { $n setSpecial; incr nsp } }
puts "OT_SPECIAL_TOP_NETS $nsp"
# S81-DIE8 10-18: the die repeater step runs BEFORE create_clock.  With the region roots declared as clocks, STA
# propagates them through the hop-0 forward cell (BUFx8 / G1 ICGx4) and repair_design silently skips every hop-0
# forwarded-clock net even though repeat_nets un-skips it (case_p4l_rv: all 140 hop-0 fclk nets 0 repeaters,
# 108 > data-1 -> fclk_mismatch FAIL).  Clock / reset distribution stays untouched by the step's own skip list
# (clock-pin + sigtype + glob dont_touch); no step check reads the SDC clock.
set ::ot_die_rep_fclk_data_ports [dict create {dsfd_dvrlyh_276_EW} {{i\[*\]} 276} {dsfd_dvrlyh_276_NS} {{i\[*\]} 276} {dsfd_dvrlyh_276_SN} {{i\[*\]} 276} {dsfd_dvrlyh_276_WE} {{i\[*\]} 276} {dsfd_dvrlyh_512_EW} {{i\[*\]} 512} {dsfd_dvrlyh_512_WE} {{i\[*\]} 512} {dsfd_dvrlyh_562_EW} {{i\[*\]} 562} {dsfd_dvrlyh_562_SN} {{i\[*\]} 562} {dsfd_dvrlyh_562_WE} {{i\[*\]} 562} {dsfd_dvrlyh_682_EW} {{i\[*\]} 682} {dsfd_dvrlyh_682_NS} {{i\[*\]} 682} {dsfd_dvrlyh_682_WE} {{i\[*\]} 682} {dsfd_dvrlyh_70_NS} {{i\[*\]} 70} {dsfd_dvrlyh_70_SN} {{i\[*\]} 70}]
# DIE-FLOW repeater step (804d68ef69adab4aca463317d74bbed100da330d)
source /work/die_repeaters_step.tcl
create_clock -name clk -period 833.333 [get_ports {ck_cl0N ck_cl0S ck_cl1N ck_cl1S ck_cl2N ck_cl2S ck_cl3N ck_cl3S ck_cl4N ck_cl4S ck_cl5N ck_cl5S ck_cl6N ck_cl6S ck_cl7N ck_cl7S ck_edge0 ck_edge8 ck_south2 ck_south3 ck_south4 ck_south5 ck_void1 ck_void3 ck_void4}]
create_clock -name ck_hbm -period 900.0 [get_ports {ck_hbm}]
set_clock_groups -asynchronous -group [get_clocks clk] -group [get_clocks ck_hbm]
set_routing_layers -signal M2-M7 -clock M5-M9
set_global_routing_layer_adjustment M2-M3 0.50
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M7 0.20
set t0 [clock seconds]
global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {[clock seconds]-$t0}]"
write_db /work/out/grt.odb
estimate_parasitics -global_routing
if {[llength [info procs ot_die_rep_post_grt_audit]]} { ot_die_rep_post_grt_audit /work/die_repeaters.post_grt.json }

puts OT_DONE
