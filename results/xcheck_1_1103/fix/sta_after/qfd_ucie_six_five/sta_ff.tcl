read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_liberty m_ff.lib
read_verilog top.v
link_design top
create_clock -name clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_timing_derate -late -data -cell_delay 1.10
set_timing_derate -late -data -net_delay 1.05
foreach n [get_nets w_*] { set_load 0.600 $n }
set_input_transition 30 [all_inputs]
puts "XCHK qfd_ucie_six_five ff L=3.0 tx=5 rx=6 clkpin=blk_rx_ck"
foreach dl {max min} {
  foreach grp {to_phy from_phy} {
    if {$grp == "to_phy"} { set ps [sta::find_timing_paths -path_delay $dl -to [get_pins u_phy/*] -group_path_count 1 -endpoint_path_count 1] } else { set ps [sta::find_timing_paths -path_delay $dl -from [get_pins u_phy/*] -group_path_count 1 -endpoint_path_count 1] }
    foreach p $ps { puts "XCHK qfd_ucie_six_five ff $dl $grp slack=[format %.1f [expr {[$p slack]*1e12}]] end=[get_full_name [$p pin]]" }
  }
}
report_check_types -min_period -violators
