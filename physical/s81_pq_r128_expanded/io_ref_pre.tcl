# DS-ROM field spine v13b ORFS step hook (PRE_CTS, PRE_GLOBAL_ROUTE): (1) the repair buffer budget raise of
# physical/abi3/v41x_karb_repair_buffer_cap.tcl (inlined: a hook is copied alone into the work dir); (2) the
# die-integration IO budget re-referenced to the boundary registers' clock pins (see io_budget_r<R>.sdc), applied
# AFTER the timing graph exists (building the graph with -reference_pin delays present segfaults OpenSTA).
if { [info procs repair_timing_helper] ne "" && [info procs ot_orig_repair_timing_helper] eq "" } {
  rename repair_timing_helper ot_orig_repair_timing_helper
  proc repair_timing_helper { args } {
    ot_orig_repair_timing_helper {*}$args -max_buffer_percent 100
  }
}
sta::worst_slack_cmd max
set fs_ref_i [get_pins {q_go$_DFF_P_/CLK}]
set fs_ref_o [get_pins {o_ready$_DFF_P_/CLK}]
set fs_in [get_ports {go i_ph* i_np* i_xbase* i_xps* i_obase* i_ops* i_fmt* x_q* r_v* r_row* r_pos* r_fp32* r_bf16* r_e* f_fault}]
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay  250 -max -clock core_clk -reference_pin $fs_ref_i $fs_in
set_input_delay  -50 -min -clock core_clk -reference_pin $fs_ref_i $fs_in
set_output_delay 250 -max -clock core_clk -reference_pin $fs_ref_o [all_outputs]
set_output_delay -50 -min -clock core_clk -reference_pin $fs_ref_o [all_outputs]
set_false_path -from [get_ports {rw_ph rw_st rw_a* rw_d* rst_n}]
puts "OT_FS_IO reference-pin budget applied (arrival in [get_property [get_pins {q_go$_DFF_P_/CLK}] arrival_max_rise] out [get_property [get_pins {o_ready$_DFF_P_/CLK}] arrival_max_rise])"
