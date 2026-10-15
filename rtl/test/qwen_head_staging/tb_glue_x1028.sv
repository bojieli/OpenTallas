`timescale 1ns/1ps
// qwen_glue_x1028 exact bench (r13 NL helper): both halves, independent same-frequency clocks (clk_i phase-shifted),
// independent resets released / re-asserted at different times. Every edge after the 3-edge local release window the
// half's q must equal the d present before that edge (one capture), and q must be 0 in its reset window; the other
// half must keep running while one half is in reset. MUT is the master's own (1 bypass, 2 bit flip; both halves).
module tb_glue_x1028;
 parameter integer MUT=0;
 reg clk_o=0,clk_i=0,rst_o_n=0,rst_i_n=0;
 always #0.416667 clk_o=~clk_o;
 initial begin #0.2; forever #0.416667 clk_i=~clk_i; end
 reg [513:0] od=0,id=0;wire [513:0] oq,iq;
 qwen_glue_x1028 #(.MUT(MUT)) dut(.clk_o(clk_o),.clk_i(clk_i),.rst_o_n(rst_o_n),.rst_i_n(rst_i_n),.od(od),.oq(oq),.id(id),.iq(iq));
 integer b,checks=0,errors=0,ao=0,ai=0,no=0,ni=0;
 reg [513:0] po=0,pi=0;
 always @(negedge clk_o) begin no=no+1;for(b=0;b<514;b=b+1) od[b]=(((no+1)*(b+3))^(no>>(b%13))^(b>>2))&1; end
 always @(negedge clk_i) begin ni=ni+1;for(b=0;b<514;b=b+1) id[b]=(((ni+7)*(b+5))^(ni>>(b%11))^(b>>3))&1; end
 always @(posedge clk_o) begin
  po=od; #0.001;
  if(!rst_o_n) ao=0; else ao=ao+1;
  if(ao>=4) begin checks=checks+514; if(oq!==po) begin errors=errors+1; if(errors<5)$display("o-half mismatch ao=%0d",ao); end end
  else if(ao<3 && oq!==0) begin errors=errors+1; if(errors<5)$display("o-half reset window ao=%0d",ao); end
 end
 always @(posedge clk_i) begin
  pi=id; #0.001;
  if(!rst_i_n) ai=0; else ai=ai+1;
  if(ai>=4) begin checks=checks+514; if(iq!==pi) begin errors=errors+1; if(errors<5)$display("i-half mismatch ai=%0d",ai); end end
  else if(ai<3 && iq!==0) begin errors=errors+1; if(errors<5)$display("i-half reset window ai=%0d",ai); end
 end
 initial begin
  repeat(6) @(negedge clk_o); rst_o_n=1;
  repeat(200) @(negedge clk_o); rst_i_n=1;
  repeat(1500) @(negedge clk_o); rst_o_n=0;          // o-half reset while i-half keeps capturing
  repeat(8) @(negedge clk_o); rst_o_n=1;
  repeat(600) @(negedge clk_o); rst_i_n=0;          // i-half reset while o-half keeps capturing
  repeat(8) @(negedge clk_o); rst_i_n=1;
  repeat(1500) @(negedge clk_o);
  if(errors||checks<3000000)$display("FAIL qwen_glue_x1028 checks=%0d errors=%0d",checks,errors);
  else $display("PASS qwen_glue_x1028 checks=%0d fixed_data_edges=1 reset_release_edges=3 independent_halves=2",checks);
  $finish;
 end
endmodule
