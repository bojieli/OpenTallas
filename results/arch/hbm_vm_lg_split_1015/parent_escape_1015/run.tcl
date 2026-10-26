set root /work
set mode $::env(MODE)
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
if {$mode eq "blocked"} {read_lef /work/blocked.lef} else {read_lef /work/child.lef}
read_liberty /work/child.lib
read_verilog /work/parent.v
link_design lg_parent_escape
initialize_floorplan -die_area {0 0 247.104 250.56} -core_area {0 0 247.104 250.56} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
set blk [ord::get_db_block]
set inst [$blk findInst u_leaf]
$inst setOrient R0
$inst setLocation 48384 49680
$inst setPlacementStatus FIRM
source /work/pins.tcl
set_routing_layers -signal M4-M6
create_clock -name core_clk -period 833.333 [get_ports clk]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set missing 0
foreach p [$inst getITerms] {if {[$p getSigType] in {POWER GROUND}} continue; if {[$p getNet] eq "NULL"} {incr missing}}
if {$missing} {error "LG_PARENT missing signal nets $missing"}
puts "LG_PARENT connectedSignalPorts=1673 missing=$missing"
write_db /work/$mode-initial.odb
pin_access -verbose 1
puts "LG_PARENT pin_access complete mode=$mode"
if {$mode eq "blocked"} {error "LG_PARENT negative unexpectedly passed pin_access"}
global_route -guide_file /work/positive.guide
write_db /work/positive-grt.odb
detailed_route -output_drc /work/positive-drc.rpt
write_db /work/positive-final.odb
write_def /work/positive-final.def
puts "LG_PARENT detailed_route complete"
