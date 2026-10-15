`timescale 1ns/1ps
module tb_tx198;
 parameter integer MUT=0;
 reg clk=0,rst_n=0; always #5 clk=~clk;
 reg [389:0] d=0; reg [389:0] old0=0,old1=0;
 always @(posedge clk) begin old0<=d;old1<=old0;end
 wire [389:0] cq;
 ot_qwen_tx198 #(.MUT(MUT)) tx(.ck({clk,clk}),.rst_n({rst_n,rst_n}),.d(d),.q(cq));
 wire [63:0] a,b;wire [7:0]fa,fb;wire ta,tb;
 ot_qwen_tile_lsl_fp1 ref_lsl(.clk(clk),.rst_n(rst_n),.v_d(old1[389]),.first_d(old1[388]),.split_d(old1[387:384]),.w_d(old1[383:128]),.x_d(old1[127:0]),.t_out(a),.lfault(fa),.tfault(ta));
 ot_qwen_tile_lsl_fp1 dut_lsl(.clk(clk),.rst_n(rst_n),.v_d(cq[389]),.first_d(cq[388]),.split_d(cq[387:384]),.w_d(cq[383:128]),.x_d(cq[127:0]),.t_out(b),.lfault(fb),.tfault(tb));
 integer c,j,checks=0,faults=0,rounds=0;reg [31:0] x,r;reg [15:0] hi;
 function [15:0] special(input integer n);begin
 case(n%16)
 0:special=16'h0000;1:special=16'h8000;2:special=16'h0001;3:special=16'h007f;
 4:special=16'h0080;5:special=16'h7f80;6:special=16'hff80;7:special=16'h7fc1;
 8:special=16'h7f81;9:special=16'h3f80;10:special=16'hbf80;11:special=16'h7f7f;
 default:special=$random;
 endcase end endfunction
 initial begin
 repeat(8)@(negedge clk);rst_n=1;
 for(c=0;c<2304;c=c+1)begin
  @(negedge clk);
  if(c==1100)rst_n=0;if(c==1116)rst_n=1;
  d[389]=(c%8==0||c%8==1);d[388]=(c%16<8);d[387:384]=(c/128)%16;
  // Compiler boot contract: no valid work during reset and local release warmup.
  if(c<32 || c>=1090 && c<1132)begin d[389]=0;d[388]=1;end
  // Initialize ALL IL8 accumulator phases, including normally invalid slots.
  if(c>=32 && c<48 || c>=1132 && c<1148)begin d[389]=1;d[388]=1;end
  for(j=0;j<12;j=j+1)begin
   hi=special(c+j*3);x={hi,16'($random)};
   // Both source modes, including ties, below/above ties, masks and exponent carry.
   if(j<4)begin
    case(c%8) 0:x[15:0]=16'h7fff;1:x[15:0]=16'h8000;2:x[15:0]=16'h8001;default:;endcase
    r=x+32'h7fff+{31'b0,x[16]};
    if(c%2)begin x=r&32'hffff0000;rounds=rounds+1;end
    if(c%11==0)x=0;
   end
   d[32*j+:32]=x;
  end
  #1;
  if(rst_n && (c>100&&c<1100||c>1216))begin
   if({a,fa,ta}!=={b,fb,tb})$fatal(1,"FAIL actual LSL canonical payload/flags c=%0d ref=%h dut=%h",c,{a,fa,ta},{b,fb,tb});
   checks=checks+1;if(|{fa,ta})faults=faults+1;
   if(cq[389:384]!==old1[389:384])$fatal(1,"FAIL TX metadata age");
   for(j=0;j<12;j=j+1)if(cq[32*j+16+:16]!==old1[32*j+16+:16])$fatal(1,"FAIL canonical upper payload ordering");
  end
 end
 if(checks<2000||faults<20||rounds<4000)$fatal(1,"FAIL coverage");
 $display("PASS TX198 actual FP32 LSL data/flags checks=%0d fault_edges=%0d rounded_inputs=%0d",checks,faults,rounds);$finish;
 end
endmodule
