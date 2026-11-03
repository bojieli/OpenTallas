read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty m_tt.lib
read_verilog top.v
link_design top
create_clock -name clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_timing_derate -late -data -cell_delay 1.10
set_timing_derate -late -data -net_delay 1.05
foreach n [get_nets w_*] { set_load 6.000 $n }
set_input_transition 30 [all_inputs]
puts "XCHK ot_qfd_serdes_112g_x12_phy_s597 tt L=30.0 tx=3 rx=3 clkpin=clk"
foreach dl {max min} {
  foreach grp {to_phy from_phy} {
    if {$grp == "to_phy"} { set ps [sta::find_timing_paths -path_delay $dl -to [get_pins u_phy/*] -group_path_count 1 -endpoint_path_count 1] } else { set ps [sta::find_timing_paths -path_delay $dl -from [get_pins u_phy/*] -group_path_count 1 -endpoint_path_count 1] }
    foreach p $ps { puts "XCHK ot_qfd_serdes_112g_x12_phy_s597 tt $dl $grp slack=[format %.1f [expr {[$p slack]*1e12}]] end=[get_full_name [$p pin]]" }
  }
}
report_check_types -min_period -violators
