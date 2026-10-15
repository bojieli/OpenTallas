`timescale 1ns/1ps
module tb_candidate_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[2439:0]scores=0;reg[19:0]p[0:0];wire[287:0]candidates;
 ot_hbm_idx_candidate_static #(.MUT(MUT))dut(.clk({4{clk}}),.rst_n(rst_n),.position(p[0]),.enable(1'b1),.*);
 reg[2439:0]src[0:512];reg[287:0]gold[0:512];reg[287:0]exp[0:2];reg[2:0]v=0;
 reg[287:0]expected=0;integer errors=0,checks=0;
 always @(posedge clk)begin
  if(rst_n)begin
   exp[0]<=expected;exp[1]<=exp[0];exp[2]<=exp[1];v<={v[1:0],scores[0]};
   #1;if(v[2])begin checks++;if(candidates!==exp[2])begin errors++;if(errors<3)$display("CAND_BAD expected%h got%h",exp[2],candidates);end end
  end
 end
 initial begin
  $readmemh("candidate_in.hex",src);$readmemh("candidate_gold.hex",gold);$readmemh("candidate_pos.hex",p);
  repeat(4)@(negedge clk);rst_n=1;
  for(integer a=0;a<513;a=a+1)begin scores=src[a];expected=gold[a];@(negedge clk);end
  scores=0;repeat(5)@(negedge clk);
  $display("IDX_CANDIDATE_STATIC MUT%0d beats%0d errors%0d",MUT,checks,errors);
  if(errors||checks!=513)$fatal(1,"exact blockmax/newest candidate mismatch");$finish;
 end
endmodule
