`timescale 1ns/1ps
module tb_qwen_ctrl_write_ledger_disabled;
 reg clk=0,rst_n=0;always #0.512 clk=~clk;
 wire w_room,sched_v,phy_row_v,phy_col_v,phy_col_we,wd_v,stop,quarantine,refresh_req,epoch_ready;
 wire[4:0]sched_bank,sched_col,phy_row_bank,phy_col_bank,phy_col_col,cancel_count;
 wire[2:0]phy_row_op;wire[18:0]phy_row_row;wire[23:0]phy_w_sec;
 wire[255:0]phy_w_data;wire[8:0]phy_w_tag,wd_tag;wire[6:0]committed_count;
 ot_qwen_ctrl_write_ledger dut(.clk(clk),.rst_n(rst_n),.w_v(1'b1),.w_sec(24'hffffff),
 .w_data(256'd0),.w_tag(9'd0),.sched_take(1'b1),.row_v(1'b1),.row_op(3'd7),
 .row_bank(5'd0),.row_row(19'd0),.col_v(1'b1),.col_we(1'b1),.col_bank(5'd0),.col_col(5'd0),
 .done_v(1'b1),.done_tag(9'd0),.ctrl_fault(1'b1),.refresh_ack(1'b1),
 .upstream_quiescent(1'b1),.epoch_advance(1'b1),.*);
 initial begin
  #1.1;rst_n=1;repeat(3)@(negedge clk);
  if({w_room,sched_v,phy_row_v,phy_col_v,phy_col_we,wd_v,stop,quarantine,refresh_req,epoch_ready,
   sched_bank,sched_col,phy_row_bank,phy_col_bank,phy_col_col,cancel_count,
   phy_row_op,phy_row_row,phy_w_sec,phy_w_data,phy_w_tag,wd_tag,committed_count} !== 367'b0)
   $fatal(1,"default-off output active");
  $display("PASS default-off");$finish;
 end
endmodule
