`timescale 1ps/1fs
module tb;
 parameter integer MUT=0;
 reg clk=0;always #416.666625 clk=~clk;
 reg rst_n=0,v=0,fp4=0;reg [1023:0] x=0;
 wire ov,nv,ofault,nfault;wire [255:0] oq,nq;wire signed [9:0] oe,ne;wire [511:0] oy,ny;
 ot_hdc_actquant original(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(ov),.q(oq),.e(oe),.y(oy),.fault(ofault));
 ot_hbm_xp_aq_tree13 #(.MUT(MUT)) candidate(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.vo(nv),.q(nq),.e(ne),.y(ny),.fault(nfault));
 integer checks=0,blocks=0;
 reg [31:0] bits;
 always @(negedge clk)if(rst_n)begin
  checks++;
  if(ov!==nv||ofault!==nfault)$fatal(1,"AQ_TREE13_CONTROL_MISMATCH check%0d",checks);
  if(ov)begin blocks++;if({oq,oe,oy}!={nq,ne,ny})$fatal(1,"AQ_TREE13_NUMERIC_MISMATCH block%0d fp4%0d e%0d/%0d",blocks,fp4,oe,ne);end
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
  if(blocks!=1024)$fatal(1,"AQ_TREE13_VACUOUS blocks%0d",blocks);
  $display("AQ_TREE13_EXACT_PASS blocks%0d elements%0d checks%0d latency13 II1 warmreset",blocks,blocks*32,checks);$finish;
 end
endmodule
