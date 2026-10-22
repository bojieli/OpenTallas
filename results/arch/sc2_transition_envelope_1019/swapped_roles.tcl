read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/ot_sram_1r1w_32x546_m1.lef
read_liberty /work/CALIBRATION_ONLY_inv_min.lib
read_liberty /work/CALIBRATION_ONLY_sram_min.lib
read_liberty /work/CALIBRATION_ONLY_inv_max.lib
read_liberty /work/CALIBRATION_ONLY_sram_max.lib
read_verilog /work/probe.v
link_design probe
set_mode calibration
create_clock -name core -period 2000 [get_ports clk]
set_clock_transition 20 [all_clocks]
define_scene TT -mode calibration -liberty_min [list /work/CALIBRATION_ONLY_inv_max.lib /work/CALIBRATION_ONLY_sram_max.lib] -liberty_max [list /work/CALIBRATION_ONLY_inv_min.lib /work/CALIBRATION_ONLY_sram_min.lib]
set_scene TT
load /work/native_accessor.so Otenvelope
set stream [open /work/swapped_role_tables.ndjson w]
puts $stream "TABLE dependent min [ot_envelope_query dependent min 2e-11 2.88e-15 {A} {Y}]"
puts $stream "TABLE capture min [ot_envelope_query capture min 2e-11 2e-11 {clk} {wd_in[0]}]"
puts $stream "TABLE dependent max [ot_envelope_query dependent max 2e-11 2.88e-15 {A} {Y}]"
puts $stream "TABLE capture max [ot_envelope_query capture max 2e-11 2e-11 {clk} {wd_in[0]}]"
close $stream
report_checks -path_delay min_max -from [get_pins {launch/rd_out[0]}] -to [get_pins {capture/wd_in[0]}] -format full_clock_expanded -digits 6
puts "MIN_ARR [get_property [get_pins dependent/Y] arrival_min_rise]"
puts "MAX_ARR [get_property [get_pins dependent/Y] arrival_max_rise]"
exit
