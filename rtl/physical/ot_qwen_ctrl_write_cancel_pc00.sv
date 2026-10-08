`timescale 1ns/1ps
// Actual receiving-edge composition. Parent still arbitrates command packets
// using eight initial controller credits; WR packets must match the offered
// native write exactly. No duplicate scheduler, PHY encoder or CDC is implied.
module ot_qwen_ctrl_write_cancel_pc00(
 input wire clk,rst_n,cmd_v,input wire[31:0]cmd,input wire[2:0]read_credit,
 output wire cmd_credit,busy,fault,
 input wire w_v,input wire[23:0]w_sec,input wire[255:0]w_data,input wire[8:0]w_tag,
 output wire w_room,sched_v,output wire[4:0]sched_bank,sched_col,
 output wire phy_row_v,output wire[2:0]phy_row_op,output wire[4:0]phy_row_bank,
 output wire[18:0]phy_row_row,output wire phy_col_v,phy_col_we,
 output wire[4:0]phy_col_bank,phy_col_col,
 output wire[23:0]phy_w_sec,output wire[255:0]phy_w_data,output wire[8:0]phy_w_tag,
 input wire done_v,input wire[8:0]done_tag,output wire wd_v,output wire[8:0]wd_tag,
 output wire cancel_v,output wire[8:0]cancel_tag,input wire cancel_take,
 output wire stop,quarantine,refresh_req,input wire refresh_ack,
 input wire upstream_quiescent,epoch_advance,output wire epoch_ready,
 output wire[4:0]cancel_count,output wire[6:0]committed_count
);
 ot_qwen_ctrl_write_cancel_service_pc #(.ENABLE(1),.PC(0)) u(.*);
endmodule
