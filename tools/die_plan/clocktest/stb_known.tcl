# KIT-OPS-6 lever 7: known-answer design for subtree_balance.tcl: one clock port, a BUF, two flops on it and ONE flop behind an inverter
# (odd parity).  STB-EDGE-1: the inverted sink must be measured on arrival_max_fall, so the tree spread is a few ps (not T/2 + a few ps).
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lef/asap7_tech_1x_201209.lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef] { read_lef $f }
foreach f [glob $P/lib/NLDM/asap7sc7p5t_*_RVT_FF_nldm_*.lib*] { read_liberty $f }
read_verilog /ct/stb_known.v
link_design stb_known
initialize_floorplan -die_area "0 0 40 40" -core_area "2 2 38 38" -site asap7sc7p5t
set blk [ord::get_db_block]
set x 3.0
foreach i [$blk getInsts] { $i setLocation [expr {int($x*1000)}] [expr {int((3.0 + 0.27*[incr n 2])*1000)}]; $i setPlacementStatus PLACED; set x [expr {$x + 3.0}] }
create_clock -name clk -period 833 [get_ports clk]
source $P/setRC.tcl
set_propagated_clock [all_clocks]
set ::env(OT_STB) report
set ::env(OT_STB_EST) placement
source /tools/subtree_balance.tcl
puts "OT_KNOWN_DONE"
