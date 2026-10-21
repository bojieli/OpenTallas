`timescale 1ns/1ps
module tb_wbk_pp_counterexample #(parameter integer MUT=0);
 reg clk=0,rst_n=0,req=0;reg [5:0] returned=0;
 wire [2:0] ready;wire grant;
 ot_wbk8_pp_credit #(.FAW(2),.NPP(2),.MUT(MUT)) u(
  .clk(clk),.rst_n(rst_n),.req(req),.returned(returned),.ready(ready),.grant(grant));
 always #5 clk=~clk;
 integer grants=0;
 always @(posedge clk)if(rst_n)begin
  if(grant)grants=grants+1;
  #1;
  if(u.cnt[0]>4||u.cnt[1]>4)
   $fatal(1,"WBK_PP_INTEGRITY unavailable expected bank granted: A=%0d B=%0d grants=%0d",u.cnt[0],u.cnt[1],grants);
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  repeat(2)@(negedge clk);req=1;
  wait(grants==8);@(negedge clk);req=0;
  if(u.cnt[0]!=4||u.cnt[1]!=4)$fatal(1,"WBK_PP_SETUP not full");
  // A then B were legitimately consumed. Independent synchronizers expose
  // B's common return while A's remains stale. This is the real capacity
  // ledger's input boundary, not a change to sealed FIFO pointer RTL.
  returned={3'd1,3'd0};@(negedge clk);returned=0;req=1;
  repeat(3)@(negedge clk);
  if(grants!=8||ready[2])$fatal(1,"WBK_PP_INTEGRITY A grant used B capacity");
  req=0;returned={3'd0,3'd1};@(negedge clk);returned=0;req=1;
  wait(grants==9);@(negedge clk);req=0;
  if(u.cnt[0]!=4||u.cnt[1]!=3)$fatal(1,"WBK_PP_INTEGRITY legitimate A progress wrong");
  $display("WBK_PP_COUNTEREXAMPLE_PASS grants=%0d A=%0d B=%0d",grants,u.cnt[0],u.cnt[1]);
  $finish;
 end
 initial begin #5000;$fatal(1,"WBK_PP_TIMEOUT");end
endmodule
