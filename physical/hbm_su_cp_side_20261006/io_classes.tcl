# Port classes of ot_hbm_su_cp_side (shared by the route SDC and the sign-off SDC).
#  die/seat class (register-to-register, crosses to the cmdproc or to the memory-control shared owner):
#   0.2 T + 150 ps against vclk at the block insertion, -min 0.
#  in-block executor class (the SU executor FSM sits in the same SU-side block; no pin stage, AGENTS
#   CLARIFICATION 10:40 "move the cut so the loop stays inside one hardened block"): inputs are executor
#   flop outputs (state==FINISHED decode / bad / logical_retired) at 0.15 T; outputs (from pin flops in the
#   adopted EXEC_OUT=1 shape) feed the executor's start / FSM-enable / request-gating cone, budgeted 0.5 T; -min 0.
set ot_T [get_property [get_clocks core_clk] period]
proc ot_apply_io {min_in} {
  global ot_T
  # die/seat class on every port, then the in-block executor ports overridden (same clock: replaces).
  set_input_delay  [expr {$ot_T * 0.2 + 150}] -clock vclk [all_inputs -no_clocks]
  set_output_delay [expr {$ot_T * 0.2 + 150}] -clock vclk [all_outputs]
  set_input_delay  [expr {$ot_T * 0.15}] -clock vclk [get_ports {exec_done exec_fault retired_original_ops*}]
  set_output_delay [expr {$ot_T * 0.5}] -clock vclk [get_ports {exec_owned new_request_permit association_fault selected_pc*}]
  set_input_delay -min $min_in -clock vclk [all_inputs -no_clocks]
  set_output_delay -min 0 -clock vclk [all_outputs]
}
