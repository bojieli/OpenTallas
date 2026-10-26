`timescale 1ns/1ps
// conservative-1011 [B hfd_hc]: hfd_hc_tile_xl (negedge clock-root lockups) vs hfd_hc_tile (positive-edge reference),
// two tiles in a chain each, the second on a root skewed by SKEW ns; real ot_dsrom_su_hcpost_lane_pr lanes (or the
// stub with STUB=1).  Every chain output (bc and acc of both tiles) must match bit for bit every cycle after warm-up.
module tb_hc_tile_xl;
parameter real SKEW=0.1;
parameter integer W=256;
parameter integer B=162;
parameter integer NCYC=600;
reg clk=0;always #0.5 clk=~clk;
reg clk_b=0; initial begin #(0.5+SKEW);clk_b=1;forever #0.5 clk_b=~clk_b;end
reg [B-1:0] head=0;reg[W-1:0] tail=0;
wire [B-1:0] rb0,rb1,xb0,xb1;wire[W-1:0] ra0,ra1,xa0,xa1;
hfd_hc_tile r0(clk,head,rb0,ra1,ra0);
hfd_hc_tile r1(clk,rb0,rb1,tail,ra1);
hfd_hc_tile_xl x0(clk,head,xb0,xa1,xa0);
hfd_hc_tile_xl x1(clk_b,xb0,xb1,tail,xa1);
integer c,b,s=17,bad=0,act=0;
initial begin if (!$value$plusargs("SEED=%d", s)) s = 17; $display("SEED=%0d", s); end
initial begin
  for(c=0;c<NCYC;c=c+1)begin
    @(negedge clk_b);#((SKEW<0 ? -SKEW : 0)+0.02);
    if(c>16 && {rb0,rb1,ra0,ra1} !== {xb0,xb1,xa0,xa1})begin bad=bad+1;if(bad<4)$display("TILE_XL_MISMATCH cycle=%0d",c);end
    if(c>16 && ra0[33:0] != 0) act=act+1;
    #0.02;
    for(b=0;b<B;b=b+1)head[b]=$random(s);
    head[B-1] = (c<4);                 // reset (rst_n = ~bcq[B-1]) for the first cycles, then run
    head[0] = (c>=4) & $random(s);     // v
    for(b=0;b<W;b=b+1)tail[b]=$random(s);
  end
  if(bad==0 && act>NCYC/4)$display("TILE_XL PASS cycles=%0d active=%0d rootskew_ns=%0.3f",NCYC,act,SKEW);
  else $display("TILE_XL FAIL mismatches=%0d active=%0d",bad,act);
  $finish;
end
endmodule
