`timescale 1ns/1ps
module tb_s81_runtime_pc_lease64;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg[63:0] source_req_v=0,source_done=0,source_quiescent=0,decode_held=0;
 reg[63:0] pc_want=0,pc_claim=0,pc_release=0;
 wire[63:0] source_issue_enable,pc_available,pc_held;wire fault;
 ot_s81_runtime_pc_lease64 #(.ENABLE(1)) dut(.*);
 integer bad=0,i;localparam[63:0] ALL=64'hffffffffffffffff;
 initial begin
  if($value$plusargs("bad=%d",bad))begin end
  repeat(3)@(negedge clk);rst_n=1;@(negedge clk);
  if(source_issue_enable!==ALL||pc_available!==0)$fatal(1,"initialgrant");
  if(bad==1)begin source_done=1;@(negedge clk);source_done=0;end
  else if(bad==2)begin pc_want=1;pc_claim=1;@(negedge clk);pc_claim=0;end
  else if(bad==3)begin dut.debt_n[17][0]=!dut.debt_n[17][0];@(negedge clk);end
  else if(bad==4)begin
   for(i=0;i<9;i=i+1)begin source_req_v=1;@(negedge clk);end source_req_v=0;
  end else begin
   // All64PCs have8actualaccepted transactions, then stopgrant. One producer
   // quiescence pulse cannot erase actualphysical completion debt.
   for(i=0;i<8;i=i+1)begin source_req_v=ALL;@(negedge clk);end source_req_v=0;
   pc_want=ALL;source_quiescent=ALL;@(negedge clk);
   if(source_issue_enable!==0||pc_available!==0)$fatal(1,"accepteddebt erased");
   for(i=0;i<8;i=i+1)begin
    source_done=ALL;@(negedge clk);
    if(i<7&&pc_available!==0)$fatal(1,"earlyavailability");
   end source_done=0;
   source_quiescent=0;@(negedge clk);
   if(pc_available!==0)$fatal(1,"missingtransportdrainack");
   source_quiescent=ALL;decode_held=64'h8000000000000001;@(negedge clk);
   if(pc_available!==(ALL^decode_held))$fatal(1,"decodeheldignored");
   decode_held=0;pc_claim=ALL;@(negedge clk);pc_claim=0;
   if(pc_held!==ALL||source_issue_enable!==0||pc_available!==0)$fatal(1,"claimownership");
   repeat(3)@(negedge clk);pc_release=ALL;@(negedge clk);pc_release=0;
   pc_want=0;source_quiescent=0;@(negedge clk);
   if(fault||pc_held!==0||source_issue_enable!==ALL)$fatal(1,"releasegrant");
   $display("RUNTIME_PC_LEASE64 PASS 64PCs eightaccepted debt actualcompletion quiescentack decodelease");$finish;
  end
  repeat(3)@(negedge clk);if(!fault)$fatal(1,"negative not rejected");
  $display("RUNTIME_PC_LEASE64 negative%0d rejected PASS",bad);$finish;
 end
endmodule
