`timescale 1ns/1ps
// TT pathfinding fixture only. Burned testjobmask is not actual per-die authority.
// Native ready interface has no pin shell; actual registered credit binding
// and IO budgets remain prerequisites for physical adoption.
module dsfd_sp_hc_cmd_bridge_pf(
 input wire clk,rst_n,
 input wire e_cmd_v,input wire[83:0] e_cmd_d,output wire e_cmd_ready,
 output wire e_done_v,output wire[7:0] e_done_tag,output wire fault,
 output wire h_cmd_valid,input wire h_cmd_ready,
 output wire[1:0] h_cmd_capture,output wire[9:0] h_cmd_user,
 output wire[20:0] h_cmd_position,output wire[3:0] h_cmd_epoch,
 input wire h_capture_done,input wire[1:0] h_done_capture,
 input wire[9:0] h_done_user,input wire[20:0] h_done_position,
 input wire[3:0] h_done_epoch,input wire h_fault

);
 ot_s81_hc_cmd_bridge #(.ENABLE(1),.OP_MASK((128'd1<<23)|(128'd1<<24)|(128'd1<<25))) u(.*);
endmodule
