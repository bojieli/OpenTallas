`timescale 1ns/1fs
module tb_qwen_ctrl_refresh_fault;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0;wire cmd_credit,row_v,col_v,col_we,busy,fault;
 wire[2:0]row_op;wire[4:0]row_bank,col_bank,col_col;wire[18:0]row_row;
 ot_qwen_ctrl_pc_protected #(.ENABLE(1),.PC(0)) dut(.clk(clk),.rst_n(rst_n),.cmd_v(1'b0),.cmd(32'b0),.read_credit(3'b0),.*);
 integer ticks=0,refs=0;real release_time,ref_due_time=121.875;
 always @(posedge clk)if(rst_n)begin
  ticks=ticks+1;if(row_v&&row_op==6)refs=refs+1;
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;release_time=$realtime;
  wait(row_v&&row_op==6);@(negedge clk);#0.001;
  // A guard rail is covered by the published single-sequential-upset model.
  // Immediate fail-closed suppression removes the due refresh command.
  dut.trip_seen=1;
  wait($realtime-release_time>ref_due_time);
  @(negedge clk);
  if(!fault || refs!=0)$fatal(1,"diagnostic setup did not expose expected first-refresh gap");
  $display("EXPECTED_REFRESH_HANDOFF_GAP elapsed_ns=%0.3f first_REF_deadline_ns=%0.3f accepted_REF=%0d sticky_fault=%b ticks=%0d",$realtime-release_time,ref_due_time,refs,fault,ticks);
  $finish;
 end
 initial begin #1000;$fatal(1,"diagnostic watchdog");end
endmodule
