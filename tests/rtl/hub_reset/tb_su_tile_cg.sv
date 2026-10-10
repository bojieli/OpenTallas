`timescale 1ns/1ps
module tb_su_tile_cg;
parameter real SKEW=0.1;
parameter integer W=448;
reg clk=0; always #0.5 clk=~clk;
reg cb=0; initial begin #(0.5+SKEW);cb=1;forever #0.5 cb=~cb;end
reg rn=0,wake=1;
wire g0,g1,w0,w1;
ot_cg_tile #(.HOLD(64),.RSTEN(0),.MUT_LATE(`ifdef OT_HUB_CG_MUT_LATE 4 `else 0 `endif)) c0(clk,rn,wake,w0,g0);
// Wake crossing has the same real falling-edge lockup as the quarter.
reg wx;always @(negedge clk)wx<=w0;
ot_cg_tile #(.HOLD(64),.RSTEN(0),.MUT_LATE(`ifdef OT_HUB_CG_MUT_LATE 4 `else 0 `endif)) c1(cb,rn,wx,w1,g1);
reg[1742:0]head=0;reg[W-1:0]tail=0;
wire[1742:0]rb0,rb1,xb0,xb1;wire[W-1:0]ra0,ra1,xa0,xa1;
hfd_su_tile_xl r0(clk,head,rb0,ra1,ra0),r1(cb,rb0,rb1,tail,ra1);
hfd_su_tile_xl x0(g0,head,xb0,xa1,xa0),x1(g1,xb0,xb1,tail,xa1);
integer c,b,window,s=27,bad=0,checks=0;
task sample;
begin
 @(negedge cb);#((SKEW<0 ? -SKEW : 0)+0.02);
 checks=checks+1;
 if({rb0,rb1,ra0,ra1}!=={xb0,xb1,xa0,xa1})begin bad=bad+1;if(bad<4)$display("TILE_CG_MISMATCH checks=%0d",checks);end
end endtask
initial begin
 repeat(20)@(posedge clk);rn=1;
 repeat(20)@(posedge clk);
 for(window=0;window<3;window=window+1)begin
  wake=0;repeat(200)@(posedge clk);#0.2;wake=1;
  repeat(3)@(posedge clk);#0.2;
  for(c=0;c<100;c=c+1)begin
   sample;
   #0.02;
   for(b=0;b<1743;b=b+1)head[b]=$random(s);
   for(b=0;b<W;b=b+1)tail[b]=$random(s);
  end
  repeat(12)sample;
 end
 if(bad==0)$display("TILE_CG PASS checks=%0d rootskew_ns=%0.3f",checks,SKEW);else $display("TILE_CG FAIL mismatches=%0d",bad);
 $finish;
end
endmodule
