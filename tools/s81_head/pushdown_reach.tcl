# HEAD-CORE-LAT-R2 c3' pushdown proof (c): are the interior M5 ft pins of the core abstract reachable from M9 at die
# level?  Tiny die = one core abstract (core_pd.lef, write_abstract_lef -bloat_occupied_layers) + 9 top pins on M9 right
# above the island; GRT then DRT of those 9 nets on M2-M9.  env OUT (holds core_pd.lef).  Result: DRT violations + opens.
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef $::env(OUT)/core_pd.lef
set m [[ord::get_db] findMaster ot_s81hd_elemA_cv]
set W [expr {[$m getWidth] / 1000.0}]
set ports {ft_ck0_i ft_ck1_i ft_mesh_i ft_mstrap_i ft_rst_i ft_ck0_o ft_ck1_o ft_mesh_o ft_rst_o}
set fh [open $::env(OUT)/reach_top.v w]
puts $fh "module reach_top([join $ports {, }]);"
foreach p $ports { puts $fh "  [expr {[string match *_i $p] ? "input" : "output"}] $p;" }
puts $fh "  ot_s81hd_elemA_cv u_core([join [lmap p $ports {format ".%s(%s)" $p $p}] {, }]);"
puts $fh "endmodule"
close $fh
read_verilog $::env(OUT)/reach_top.v
link_design reach_top
set D [expr {$W + 21.6}]
initialize_floorplan -die_area "0 0 $D $D" -core_area "0 0 $D $D" -site asap7sc7p5t
source $P/make_tracks.tcl
set u [ord::get_db_block]
set i [$u findInst u_core]; $i setLocation 10800 10800; $i setPlacementStatus FIXED
# top pins on M9 above each core ft pin (core pin centre + 10.8 offset)
foreach p $ports {
  set it [$i findITerm $p]; set bb [$it getBBox]
  set x [expr {([$bb xMin] + [$bb xMax]) / 2000.0}]; set y [expr {([$bb yMin] + [$bb yMax]) / 2000.0}]
  place_pin -pin_name $p -layer M9 -location "$x $y" -pin_size {0.4 0.4}
  puts "REACH_PIN $p core_m5 ($x,$y)"
}
set_routing_layers -signal M2-M9
global_route -verbose
detailed_route -output_drc $::env(OUT)/reach_drc.rpt -verbose 0
set nv 0; catch { set fh [open $::env(OUT)/reach_drc.rpt]; set nv [regexp -all {violation type} [read $fh]]; close $fh }
puts "REACH_RESULT drc_violations $nv"
check_antennas
foreach p $ports { set n [$u findNet $p]; puts "REACH_NET $p wires [expr {[$n getWire] eq "NULL" ? 0 : 1}]" }
