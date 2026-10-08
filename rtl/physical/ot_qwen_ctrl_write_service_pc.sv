`timescale 1ns/1ps
// Actual receiving-edge composition. Parent still arbitrates command packets
// using eight initial controller credits; WR packets must match the offered
// native write exactly. No duplicate scheduler, PHY encoder or CDC is implied.
module ot_qwen_ctrl_write_service_pc #(parameter integer ENABLE=0, PC=0, PHASE=0)(
 input wire clk,rst_n,cmd_v,input wire[31:0]cmd,input wire[2:0]read_credit,
 output wire cmd_credit,busy,fault,
 input wire w_v,input wire[23:0]w_sec,input wire[255:0]w_data,input wire[8:0]w_tag,
 output wire w_room,sched_v,output wire[4:0]sched_bank,sched_col,
 output wire phy_row_v,output wire[2:0]phy_row_op,output wire[4:0]phy_row_bank,
 output wire[18:0]phy_row_row,output wire phy_col_v,phy_col_we,
 output wire[4:0]phy_col_bank,phy_col_col,
 output wire[23:0]phy_w_sec,output wire[255:0]phy_w_data,output wire[8:0]phy_w_tag,
 input wire done_v,input wire[8:0]done_tag,output wire wd_v,output wire[8:0]wd_tag,
 output wire stop,quarantine,refresh_req,input wire refresh_ack,
 input wire upstream_quiescent,epoch_advance,output wire epoch_ready,
 output wire[4:0]cancel_count,output wire[6:0]committed_count
);
 wire row_v,col_v,col_we,core_busy,core_fault,core_credit;
 wire[2:0]row_op;wire[4:0]row_bank,col_bank,col_col;wire[18:0]row_row;
 (* keep=1,dont_touch=1 *)reg contract_trip;
 (* keep=1,dont_touch=1 *)reg contract_permit;
 wire contract_bad=cmd_v && cmd[31:30]==2 &&
   (!sched_v || cmd[9:0]!={sched_col,sched_bank});
 wire contract_halt=contract_trip || !contract_permit || contract_bad;
 wire ledger_fault=core_fault || contract_trip || !contract_permit;
 wire accepted_cmd=(ENABLE!=0) && rst_n && cmd_v && !stop && !contract_halt;
 wire sched_take=accepted_cmd && cmd[31:30]==2;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin contract_trip<=0;contract_permit<=1;end
  else if(ENABLE!=0 && contract_halt)begin contract_trip<=1;contract_permit<=0;end
 ot_qwen_ctrl_pc_protected #(.ENABLE(ENABLE),.PC(PC),.PHASE(PHASE)) controller(
 .clk(clk),.rst_n(rst_n),.cmd_v(accepted_cmd),.cmd(cmd),
 .read_credit(stop?3'b0:read_credit),.cmd_credit(core_credit),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
 .col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),
 .busy(core_busy),.fault(core_fault));
 ot_qwen_ctrl_write_ledger #(.ENABLE(ENABLE),.PC(PC)) ownership(
 .ctrl_fault(ledger_fault),.*);
 assign cmd_credit=core_credit && !stop;
 assign busy=core_busy && !stop;
 assign fault=(ENABLE!=0) && rst_n &&
   (core_fault || contract_trip || !contract_permit || quarantine);
endmodule
