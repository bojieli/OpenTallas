`timescale 1ns/1ps
`default_nettype none
// Bench of ot_hbm_xp_aq_tree13_fmt (G-SMVM-AQFP4): the parameterised-mode leaf is cycle- and bit-identical to the closed
// ot_hbm_xp_aq_tree13 with fp4 driven to the same constant, for FP4=0 (the x-load) and FP4=1, on random finite blocks
// (incl. zero / tiny / large magnitudes) with random valid gaps.  Negative control: the FP4=0 leaf against the
// reference with fp4=1 must differ (proves the mode reaches the arithmetic), and MUT=1 of the leaf must differ.
module tb_hbm_xp_aq_tree13_fmt;
 parameter integer FP4=0, REF_FP4=0, MUT=0;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg v;reg[1023:0]x;
 wire vo_a,vo_b,f_a,f_b;wire[255:0]q_a,q_b;wire signed[9:0]e_a,e_b;wire[511:0]y_a,y_b;
 ot_hbm_xp_aq_tree13_fmt #(.FP4(FP4),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.vo(vo_a),.q(q_a),.e(e_a),.y(y_a),.fault(f_a));
 ot_hbm_xp_aq_tree13 #(.MUT(0)) ref0(.clk(clk),.rst_n(rst_n),.v(v),.fp4(REF_FP4[0]),.x(x),.vo(vo_b),.q(q_b),.e(e_b),.y(y_b),.fault(f_b));
 integer c,i,mism=0,blocks=0;reg[31:0]w;
 initial begin
  v=0;x=0;#5 rst_n=1;
  for(c=0;c<3000;c=c+1)begin
   @(negedge clk);
   v=($urandom%4)!=0;
   for(i=0;i<32;i=i+1)begin
    w=$urandom; case($urandom%4) 0:w[30:23]=8'd127+($urandom%8)-4; 1:w[30:23]=8'd60+($urandom%8); 2:w[30:23]=8'd150+($urandom%20); default: w[30:0]=($urandom%8==0)?31'd0:w[30:0]; endcase
    if(w[30:23]==8'hff)w[30:23]=8'hfe;
    x[32*i+:32]=w;
   end
   if(v)blocks=blocks+1;
  end
  repeat(20)@(negedge clk);
  $display("%s tb_hbm_xp_aq_tree13_fmt FP4=%0d REF_FP4=%0d MUT=%0d blocks=%0d mismatching_cycles=%0d",mism==0?"PASS":"DIFF",FP4,REF_FP4,MUT,blocks,mism);
  $finish;
 end
 always @(posedge clk) if(rst_n) if({vo_a,f_a}!=={vo_b,f_b} || (vo_b && {q_a,e_a,y_a}!=={q_b,e_b,y_b})) mism=mism+1;
endmodule
`default_nettype wire
