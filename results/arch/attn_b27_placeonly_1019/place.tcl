set p /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $p/lef/asap7_tech_1x_201209.lef
read_lef $p/lef/asap7sc7p5t_28_R_1x_220121a.lef
define_corners tt ff
foreach corner {TT FF} scene {tt ff} {
 foreach stem {AO_RVT_%s_nldm_211120.lib.gz INVBUF_RVT_%s_nldm_220122.lib.gz OA_RVT_%s_nldm_211120.lib.gz SEQ_RVT_%s_nldm_220123.lib SIMPLE_RVT_%s_nldm_211120.lib.gz} {set f [format $stem $corner]; read_liberty -corner $scene $p/lib/NLDM/asap7sc7p5t_$f}
}
read_verilog /input/physical.v
link_design qkd_kvs_attn_fl
add_global_connection -net VDD -pin_pattern ^VDD$ -power
add_global_connection -net VSS -pin_pattern ^VSS$ -ground
global_connect
read_def -floorplan_initialize /out/floorplan_only.def
set b [ord::get_db_block]
foreach net [$b getNets] {if {[$net getSigType] eq "POWER" || [$net getSigType] eq "GROUND"} {puts "PG_IMPORT [$net getName] swires=[llength [$net getSWires]]"}}
set n 0; set ff 0
foreach i [$b getInsts] {
 incr n
 if {[string match DFF* [[$i getMaster] getName]]} {incr ff}
 if {[string match u_core.* [$i getName]]} {error "GHOST_OLD_COMPONENT [$i getName]"}
}
puts "IMPORT_COUNTS cells=$n ff=$ff"
if {$n != 34603 || $ff != 6403} {error "IMPORT_COUNT_MISMATCH"}
write_verilog /out/import.v
write_db /out/import.odb
source /input/verify_import.tcl
# Diagnostic ideal-clock placement timing only: physical clock insertion and parent reference are NULL.
create_clock -name core_clk -period 833.333 [get_ports ck]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
source $p/setRC.tcl
set ::env(RESULTS_DIR) /out
set_routing_layers -signal M2-M5 -clock M2-M5
set ::env(OT_OFLOP_COLS) 4
set ::env(OT_OFLOP_HOPS) 8
set ::env(OT_OFLOP_ALLOW_NONE) 1
source /input/io_flop_at_pins.tcl
set_placement_padding -global -left 0 -right 0
global_placement -density 0.5 -skip_io -routability_driven
source /input/out_flop_release.tcl
detailed_placement
check_placement -verbose
write_db /out/placed.odb
write_verilog /out/placed.v
estimate_parasitics -placement
report_checks -path_delay max -group_path_count 100 -format full_clock_expanded -fields {slew cap fanout input_pin net} > /out/setup_tt.txt
report_checks -path_delay min -corner ff -group_path_count 100 -format full_clock_expanded -fields {slew cap fanout input_pin net} > /out/hold_ff.txt
report_checks -from [get_pins c14180/QN] -to [get_pins cpo216_ff/D] -path_delay max -format full_clock_expanded -fields {slew cap fanout input_pin net} > /out/critical_cone_tt.txt
report_check_types -max_slew -max_capacitance -max_fanout -violators > /out/electrical.txt
source /input/fp_margin_lint.tcl
ot_fp_lint_dump /out/placed_graph.json
set ::env(OT_LAYOUT_OUT) /out/layout.json
set ::env(OT_LAYOUT_CLOCKS) ck
source /input/layout_dump.tcl
puts "PLACEMENT_ONLY_FINISHED_NO_CTS_NO_ROUTE_NO_RESIZE"
exit
