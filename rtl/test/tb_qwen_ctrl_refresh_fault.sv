`timescale 1ns/1fs
module tb_qwen_ctrl_refresh_fault;
 parameter integer INJECT=1;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0;wire cmd_credit,row_v,col_v,col_we,busy,fault;
 wire[2:0]row_op;wire[4:0]row_bank,col_bank,col_col;wire[18:0]row_row;
 ot_qwen_ctrl_pc_protected #(.ENABLE(1),.PC(0)) dut(.clk(clk),.rst_n(rst_n),.cmd_v(1'b0),.cmd(32'b0),.read_credit(3'b0),.*);
 integer ticks=0,refs=0;real release_time,ref_due_time=121.875;
 always @(posedge clk)if(rst_n)begin
  ticks=ticks+1;if(row_v&&row_op==6)begin
   refs=refs+1;
   if((ticks-1)*1024>121875 && refs==1)$fatal(1,"baseline first REF missed absolute epoch");
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;release_time=$realtime;
  wait(row_v&&row_op==6);@(negedge clk);#0.001;
  // A guard rail is covered by the published single-sequential-upset model.
  // Immediate fail-closed suppression removes the due refresh command.
  if(INJECT)dut.trip_seen=1;
  wait(ticks>=121);
  @(negedge clk);
  if(INJECT && (!fault || refs!=0))$fatal(1,"diagnostic setup did not expose expected first-refresh gap");
  if(!INJECT && (fault || refs!=1))$fatal(1,"baseline setup invalid");
  $display("REFRESH_DIAGNOSTIC injected=%0d virtual_epoch_elapsed_ns=%0.3f first_REF_deadline_ns=%0.3f accepted_REF=%0d sticky_fault=%b ticks=%0d",INJECT,(ticks-1)*1.024,ref_due_time,refs,fault,ticks);
  $finish;
 end
 initial begin #1000;$fatal(1,"diagnostic watchdog");end
endmodule
