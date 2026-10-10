`timescale 1ns/1ps
module tb_su_tile_xl;
parameter real SKEW=0.1;
reg clk=0;always #0.5 clk=~clk;
reg clk_b=0; initial begin #(0.5+SKEW);clk_b=1;forever #0.5 clk_b=~clk_b;end
reg [1742:0] head=0;reg[447:0] tail=0;
wire [1742:0] rb0,rb1,xb0,xb1;wire[447:0] ra0,ra1,xa0,xa1;
hfd_su_tile r0(clk,head,rb0,ra1,ra0);
hfd_su_tile r1(clk,rb0,rb1,tail,ra1);
hfd_su_tile_xl x0(clk,head,xb0,xa1,xa0);
hfd_su_tile_xl x1(clk_b,xb0,xb1,tail,xa1);
integer c,b,s=17,bad=0;
initial begin
  for(c=0;c<300;c=c+1)begin
    @(negedge clk_b);#((SKEW<0 ? -SKEW : 0)+0.02);
    if(c>12 && {rb0,rb1,ra0,ra1} !== {xb0,xb1,xa0,xa1})begin bad=bad+1;if(bad<4)$display("TILE_XL_MISMATCH cycle=%0d",c);end
    #0.02;
    for(b=0;b<1743;b=b+1)head[b]=$random(s);
    for(b=0;b<448;b=b+1)tail[b]=$random(s);
  end
  if(bad==0)$display("TILE_XL PASS cycles=300 rootskew_ns=%0.3f",SKEW);else $display("TILE_XL FAIL mismatches=%0d",bad);
  $finish;
end
endmodule
