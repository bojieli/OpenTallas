`timescale 1ns/1ps
module tb_idx_score_fault;
 parameter integer MUT=0;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg[17:0]score=0;reg[3:0]protocol=0;wire fault;integer checked=0;
 ot_hbm_idx_score_fault_static #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.score_status(score),.protocol_fault(protocol),.fault(fault));
 task tick;begin @(posedge clk);#1;end endtask
 task run_case(input bit valid,input[7:0]kv,input[7:0]fl,input[3:0]pf,input bit expected);
 begin
  @(negedge clk);rst_n=0;score=0;protocol=0;tick();@(negedge clk);rst_n=1;
  score={kv,fl,1'b1,valid};protocol=pf;tick();
  if(fault!==expected)$fatal(1,"IDX_SCORE_FAULT_FAIL valid=%b kv=%h fl=%h pf=%h got=%b expected=%b",valid,kv,fl,pf,fault,expected);
  @(negedge clk);score=0;protocol=0;
  repeat(4)begin tick();if(fault!==expected)$fatal(1,"IDX_SCORE_FAULT_FAIL sticky changed");end
  checked++;
 end endtask
 initial begin
  for(integer l=0;l<8;l++)begin
   run_case(1,8'b1<<l,8'b1<<l,0,1);
   run_case(0,8'b1<<l,8'b1<<l,0,0);
   run_case(1,0,8'b1<<l,0,0);
   run_case(1,8'b1<<((l+1)%8),8'b1<<l,0,0);
  end
  for(integer p=0;p<4;p++)run_case(0,0,0,4'b1<<p,1);
  run_case(1,8'hff,0,0,0);
  $display("IDX_SCORE_FAULT_PASS cases=%0d all8lanes valid/keyvalid guards oldprotocol sticky",checked);$finish;
 end
endmodule
