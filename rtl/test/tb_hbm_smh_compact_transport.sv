`timescale 1ns/1ps
module tb_hbm_smh_compact_transport;
 localparam integer R=818,B=2069,N=13;
 reg clk=0,rst_a=0;
 always #0.416666 clk=~clk;
 reg [2*R-1:0] rin;
 reg [B-1:0] bin;
 wire [2*R-1:0] rpm0,rpm1,ro0,ro1;
 wire [B-1:0] bm0,bm1,bo0,bo1,bn0,bn1,bs0,bs1;
 wire [R-1:0] rn0,rn1,rs0,rs1;
 wire [N-1:0] on0,on1,os0,os1;
 ot_hbm_accel_smh_pt_w w0(.clk(clk),.rst_a(rst_a),.rin(rin),.bin(bin),.rpm(rpm0),.bm(bm0),
  .rl1_n(rn0),.rl1_s(rs0),.bk1_n(bn0),.bk1_s(bs0),.ohl1_n(on0),.ohl1_s(os0));
 ot_hbm_smh_compact_pt_w w1(.clk(clk),.rst_a(rst_a),.rin(rin),.bin(bin),.rpm(rpm1),.bm(bm1),
  .rl1_n(rn1),.rl1_s(rs1),.bk1_n(bn1),.bk1_s(bs1),.ohl1_n(on1),.ohl1_s(os1));
 ot_hbm_accel_smh_pt_e e0(.clk(clk),.rst_a(rst_a),.rpm(rpm0),.bm(bm0),.rout(ro0),.bout(bo0));
 ot_hbm_smh_compact_pt_e e1(.clk(clk),.rst_a(rst_a),.rpm(rpm1),.bm(bm1),.rout(ro1),.bout(bo1));
 integer i,j,checks=0;
 reg [31:0] rng=32'h974ab105;
 function [31:0] random_word;
  input [31:0] x;
  reg [31:0] y;
  begin y=x^(x<<13); y=y^(y>>17); random_word=y^(y<<5); end
 endfunction
 initial begin
  rin=0;bin=0;
  for(i=0;i<4096;i=i+1) begin
   @(negedge clk);
   // Live reset, drain bubbles, and full-width independent random words.
   rst_a=(i>=5 && !(i>=997 && i<1002) && !(i>=2045 && i<2049));
   for(j=0;j<2*R;j=j+1) begin rng=random_word(rng);rin[j]=rng[9];end
   for(j=0;j<B;j=j+1) begin rng=random_word(rng);bin[j]=rng[17];end
   @(posedge clk);#0.01;
   if(i>8) begin
    if ({rpm0,bm0,rn0,rs0,bn0,bs0,on0,os0,ro0,bo0} !==
        {rpm1,bm1,rn1,rs1,bn1,bs1,on1,os1,ro1,bo1})
      $fatal(1,"COMPACT EXACT FAIL cycle=%0d",i);
    checks=checks+1;
   end
  end
  $display("COMPACT EXACT PASS cycles=4096 checks=%0d width_r=%0d width_b=%0d stages=4",checks,R,B);
  $finish;
 end
endmodule
