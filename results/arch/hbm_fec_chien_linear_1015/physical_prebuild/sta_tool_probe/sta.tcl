read_liberty {/srv/opentallas-scratch/codex/fec-chien-linear-1015/tt_libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib}
read_liberty {/srv/opentallas-scratch/codex/fec-chien-linear-1015/tt_libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib}
read_liberty {/srv/opentallas-scratch/codex/fec-chien-linear-1015/tt_libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib}
read_liberty {/srv/opentallas-scratch/codex/fec-chien-linear-1015/tt_libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty {/srv/opentallas-scratch/codex/fec-chien-linear-1015/tt_libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib}
read_verilog {/srv/opentallas-scratch/codex/fec-chien-linear-1015/sta_tool_probe_input/mapped.v}
link_design probe
set_units -time ps
create_clock -name clk -period 885.416666666667 [get_ports {clk}]
create_clock -name clk_collect -period 885.416666666667 [get_ports {clk_collect}]
create_clock -name clk_encode -period 885.416666666667 [get_ports {clk_encode}]
create_clock -name clk_codeword -period 885.416666666667 [get_ports {clk_codeword}]
create_clock -name pma_rck -period 885.416666666667 [get_ports {pma_rck}]
create_clock -name rclk_syndrome -period 885.416666666667 [get_ports {rclk_syndrome}]
create_clock -name rclk_bm0 -period 885.416666666667 [get_ports {rclk_bm0}]
create_clock -name rclk_bm1 -period 885.416666666667 [get_ports {rclk_bm1}]
create_clock -name rclk_bm2 -period 885.416666666667 [get_ports {rclk_bm2}]
create_clock -name rclk_bm3 -period 885.416666666667 [get_ports {rclk_bm3}]
create_clock -name rclk_chien -period 885.416666666667 [get_ports {rclk_chien}]
create_clock -name rclk_emit -period 885.416666666667 [get_ports {rclk_emit}]
set_case_analysis 1 [get_ports rst_n]
set data_inputs {}
foreach p [all_inputs] { if {[lsearch -exact {clk clk_collect clk_encode clk_codeword pma_rck rclk_syndrome rclk_bm0 rclk_bm1 rclk_bm2 rclk_bm3 rclk_chien rclk_emit rst_n} [get_full_name $p]] < 0} { lappend data_inputs $p } }
set_input_delay 0 -clock clk $data_inputs
set_output_delay 0 -clock clk [all_outputs]
check_setup -verbose
report_checks -path_delay max -group_path_count 64 -format full_clock_expanded -fields {capacitance slew fanout input_pin net} -digits 4 > {/srv/opentallas-scratch/codex/fec-chien-linear-1015/sta_tool_probe_2/max_paths.txt}
report_checks -path_delay min -group_path_count 16 -format full_clock_expanded -fields {capacitance slew fanout input_pin net} -digits 4 > {/srv/opentallas-scratch/codex/fec-chien-linear-1015/sta_tool_probe_2/min_paths.txt}
report_checks -unconstrained -group_path_count 16 -digits 4 > {/srv/opentallas-scratch/codex/fec-chien-linear-1015/sta_tool_probe_2/unconstrained.txt}
report_worst_slack -max
report_worst_slack -min
report_tns
exit
