`timescale 1ps/1fs
// HNX-GQ s3 (L2H-P3/GQ 10-19): lockstep bench of ot_hnx_coll_aq14 against the golden-bound RTL ot_hdc_actquant (the
// closed tree13 bench physical/hbm_xp_aq_tree13_1014/tb_aq_tree13.sv, same 1,024 FP8 + FP4 blocks incl. zeros, -0,
// subnormals, max, Inf / NaN faults and 3 warm resets), with the reference outputs delayed ONE edge (LATENCY 14 vs 13)
// and the biased exponent copies checked (eb == e + 127 in every copy). Prints AQ14_EXACT_PASS or fatals with
// AQ14_*_MISMATCH. Mutants: LMUT (SRAM ring one slot short), +define+OT_HNX_AQ_MUT_EC (one element's exponent copy off
// by one), +define+OT_HNX_AQ_MUT_RS (one element's shift-count copy off by one) must all fail.
module tb;
 parameter integer LMUT=0;
 reg clk=0;always #416.666625 clk=~clk;
 reg rst_n=0,v=0,fp4=0;reg [1023:0] x=0;
 wire ov,nv,ofault,nfault;wire [255:0] oq,nq;wire signed [9:0] oe,ne;wire [511:0] oy,ny;wire [31:0] neb;
 ot_hdc_actquant original(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(ov),.q(oq),.e(oe),.y(oy),.fault(ofault));
 ot_hnx_coll_aq14 #(.LMUT(LMUT),.EBC(4)) candidate(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(nv),.q(nq),.e(ne),.y(ny),
   .eb(neb),.fault(nfault));
 // reference delayed one edge (valid / fault cleared by reset like the candidate's output flops)
 reg dv,dfault;reg [255:0] dq;reg signed [9:0] de;reg [511:0] dy;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin dv<=0;dfault<=0;end else begin dv<=ov;dfault<=ofault;end
 always @(posedge clk)begin dq<=oq;de<=oe;dy<=oy;end
 integer checks=0,blocks=0;
 reg [31:0] bits;
 always @(negedge clk)if(rst_n)begin
  checks++;
  if(dv!==nv||dfault!==nfault)$fatal(1,"AQ14_CONTROL_MISMATCH check%0d",checks);
  if(dv)begin blocks++;
   if({dq,de,dy}!=={nq,ne,ny})$fatal(1,"AQ14_NUMERIC_MISMATCH block%0d fp4%0d e%0d/%0d",blocks,fp4,de,ne);
   for(integer c=0;c<4;c++)if(neb[8*c+:8]!==8'(de+10'sd127))$fatal(1,"AQ14_EB_MISMATCH block%0d copy%0d",blocks,c);
  end
 end
 initial begin
  repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);
  for(integer f=0;f<1024;f++)begin
   @(negedge clk);v=1;fp4=f[0];
   for(integer i=0;i<32;i++)begin
    bits=32'(f*104729+i*65537+1);bits[30:23]=8'((f*17+i*31)%255);
    case(f%16)
     0:bits=0;
     1:bits=32'h80000000;
     2:bits=32'(i+1);
     3:bits=32'h7f7fffff-32'(i);
     4:bits=32'h00800000+32'(i);
     5:bits=32'h3f800000+(32'(i)<<12);
     6:bits=32'h7f800000;
     7:bits=32'h7fc00000+32'(i);
    endcase
    x[i*32+:32]=bits;
   end
   if(f%257==256)begin @(negedge clk);v=0;repeat(20)@(negedge clk);rst_n=0;repeat(5)@(negedge clk);rst_n=1;repeat(5)@(negedge clk);end
  end
  @(negedge clk);v=0;repeat(25)@(negedge clk);
  if(blocks!=1024)$fatal(1,"AQ14_VACUOUS blocks%0d",blocks);
  $display("AQ14_EXACT_PASS blocks%0d elements%0d checks%0d latency14 II1 warmreset eb4",blocks,blocks*32,checks);$finish;
 end
endmodule
