set p /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach family {AO INVBUF OA SIMPLE} {
 foreach f [glob $p/asap7sc7p5t_${family}_RVT_TT_*.lib.gz] { read_liberty $f }
}
read_liberty $p/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog out/sta_netlist.v
link_design hidx_coupon1
create_clock -name coupon_clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks coupon_clk]
set_clock_uncertainty -hold 25 [get_clocks coupon_clk]
set_input_delay 0 -clock coupon_clk [get_ports {lane_v* payload*}]
set_output_delay 0 -clock coupon_clk [get_ports {compacted* pair_select* quad_select*}]
report_checks -path_delay max -group_count 12 -fields {slew cap fanout input_pin nets} -digits 6
report_check_types -max_slew -max_capacitance -violators
exit
