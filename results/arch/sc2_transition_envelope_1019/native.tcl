read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/ot_sram_1r1w_32x546_m1.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_liberty /work/ot_sram_1r1w_32x546_m1_tt.lib
read_verilog /work/probe.v
link_design probe
set_mode calibration
create_clock -name core -period 2000 [get_ports clk]
set_clock_transition 20 [all_clocks]
define_scene TT -mode calibration -liberty_min [list /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz /work/ot_sram_1r1w_32x546_m1_tt.lib] -liberty_max [list /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz /work/ot_sram_1r1w_32x546_m1_tt.lib]
set_scene TT
load /work/native_accessor.so Otenvelope
set stream [open /work/tables.ndjson w]
puts $stream "TABLE dependent min [ot_envelope_query dependent min 0 0 {A} {Y}]"
puts $stream "TABLE dependent min [ot_envelope_query dependent min 0 7.2e-16 {A} {Y}]"
puts $stream "TABLE dependent min [ot_envelope_query dependent min 5e-12 7.2e-16 {A} {Y}]"
puts $stream "TABLE dependent min [ot_envelope_query dependent min 2.5e-12 1e-15 {A} {Y}]"
puts $stream "TABLE dependent min [ot_envelope_query dependent min 2e-11 2.88e-15 {A} {Y}]"
puts $stream "TABLE dependent min [ot_envelope_query dependent min 3.2e-10 4.608e-14 {A} {Y}]"
puts $stream "TABLE dependent min [ot_envelope_query dependent min 8e-10 4.608e-14 {A} {Y}]"
puts $stream "TABLE launch min [ot_envelope_query launch min 0 0 {clk} {rd_out[0]}]"
puts $stream "TABLE launch min [ot_envelope_query launch min 0 7.2e-16 {clk} {rd_out[0]}]"
puts $stream "TABLE launch min [ot_envelope_query launch min 5e-12 7.2e-16 {clk} {rd_out[0]}]"
puts $stream "TABLE launch min [ot_envelope_query launch min 2.5e-12 1e-15 {clk} {rd_out[0]}]"
puts $stream "TABLE launch min [ot_envelope_query launch min 2e-11 2.88e-15 {clk} {rd_out[0]}]"
puts $stream "TABLE launch min [ot_envelope_query launch min 3.2e-10 4.608e-14 {clk} {rd_out[0]}]"
puts $stream "TABLE launch min [ot_envelope_query launch min 8e-10 4.608e-14 {clk} {rd_out[0]}]"
puts $stream "TABLE capture min [ot_envelope_query capture min 0 0 {clk} {wd_in[0]}]"
puts $stream "TABLE capture min [ot_envelope_query capture min 0 7.2e-16 {clk} {wd_in[0]}]"
puts $stream "TABLE capture min [ot_envelope_query capture min 5e-12 7.2e-16 {clk} {wd_in[0]}]"
puts $stream "TABLE capture min [ot_envelope_query capture min 2.5e-12 1e-15 {clk} {wd_in[0]}]"
puts $stream "TABLE capture min [ot_envelope_query capture min 2e-11 2.88e-15 {clk} {wd_in[0]}]"
puts $stream "TABLE capture min [ot_envelope_query capture min 3.2e-10 4.608e-14 {clk} {wd_in[0]}]"
puts $stream "TABLE capture min [ot_envelope_query capture min 8e-10 4.608e-14 {clk} {wd_in[0]}]"
puts $stream "TABLE dependent max [ot_envelope_query dependent max 0 0 {A} {Y}]"
puts $stream "TABLE dependent max [ot_envelope_query dependent max 0 7.2e-16 {A} {Y}]"
puts $stream "TABLE dependent max [ot_envelope_query dependent max 5e-12 7.2e-16 {A} {Y}]"
puts $stream "TABLE dependent max [ot_envelope_query dependent max 2.5e-12 1e-15 {A} {Y}]"
puts $stream "TABLE dependent max [ot_envelope_query dependent max 2e-11 2.88e-15 {A} {Y}]"
puts $stream "TABLE dependent max [ot_envelope_query dependent max 3.2e-10 4.608e-14 {A} {Y}]"
puts $stream "TABLE dependent max [ot_envelope_query dependent max 8e-10 4.608e-14 {A} {Y}]"
puts $stream "TABLE launch max [ot_envelope_query launch max 0 0 {clk} {rd_out[0]}]"
puts $stream "TABLE launch max [ot_envelope_query launch max 0 7.2e-16 {clk} {rd_out[0]}]"
puts $stream "TABLE launch max [ot_envelope_query launch max 5e-12 7.2e-16 {clk} {rd_out[0]}]"
puts $stream "TABLE launch max [ot_envelope_query launch max 2.5e-12 1e-15 {clk} {rd_out[0]}]"
puts $stream "TABLE launch max [ot_envelope_query launch max 2e-11 2.88e-15 {clk} {rd_out[0]}]"
puts $stream "TABLE launch max [ot_envelope_query launch max 3.2e-10 4.608e-14 {clk} {rd_out[0]}]"
puts $stream "TABLE launch max [ot_envelope_query launch max 8e-10 4.608e-14 {clk} {rd_out[0]}]"
puts $stream "TABLE capture max [ot_envelope_query capture max 0 0 {clk} {wd_in[0]}]"
puts $stream "TABLE capture max [ot_envelope_query capture max 0 7.2e-16 {clk} {wd_in[0]}]"
puts $stream "TABLE capture max [ot_envelope_query capture max 5e-12 7.2e-16 {clk} {wd_in[0]}]"
puts $stream "TABLE capture max [ot_envelope_query capture max 2.5e-12 1e-15 {clk} {wd_in[0]}]"
puts $stream "TABLE capture max [ot_envelope_query capture max 2e-11 2.88e-15 {clk} {wd_in[0]}]"
puts $stream "TABLE capture max [ot_envelope_query capture max 3.2e-10 4.608e-14 {clk} {wd_in[0]}]"
puts $stream "TABLE capture max [ot_envelope_query capture max 8e-10 4.608e-14 {clk} {wd_in[0]}]"
close $stream
report_checks -path_delay min_max -from [get_pins {launch/rd_out[0]}] -to [get_pins {capture/wd_in[0]}] -format full_clock_expanded -digits 6
puts "MIN_ARR [get_property [get_pins dependent/Y] arrival_min_rise]"
puts "MAX_ARR [get_property [get_pins dependent/Y] arrival_max_rise]"
exit
