// HBM-FORM-SPLIT-14-SUX lock-step: DUT pinned bank WCOPY=W vs reference WCOPY=0 whose write inputs are delayed D edges.
// D=1 is the declared +1 PIN CYCLE: identical read_data / read_return every cycle. A narrow address range makes reads
// hit recent writes, so a commit-timing error is visible (control D=0 must FAIL).
`timescale 1ns/1ps
`ifndef W
 `define W 1
`endif
`ifndef D
 `define D 1
`endif
`ifndef MC
 `define MC 0
`endif
`ifndef MW
 `define MW 0
`endif
module tb;
 reg clk=0,rst_n=0; always #5 clk=~clk;
 reg[5:0]rv=0;reg[53:0]ra=0;reg wv=0;reg[8:0]wa=0;reg[31:0]wd=0;
 reg wv1=0;reg[8:0]wa1=0;reg[31:0]wd1=0;
 wire wvr=(`D!=0)?wv1:wv;wire[8:0]war=(`D!=0)?wa1:wa;wire[31:0]wdr=(`D!=0)?wd1:wd;
 wire[191:0]qd,qr;wire[5:0]vd,vr;
 ot_hbm_su_static_pinned_bank #(.READERS(6),.RB(9),.WCOPY(`W),.MUT_COHERENCE(`MC),.MUT_WCOPY(`MW))dut(.clk(clk),.rst_n(rst_n),.clk_rd(clk),.clk_ws(clk),.clk_macro({6{clk}}),
  .read_v(rv),.read_addr(ra),.read_data(qd),.read_return(vd),.write_v(wv),.write_addr(wa),.write_data(wd));
 ot_hbm_su_static_pinned_bank #(.READERS(6),.RB(9),.WCOPY(0))ref_b(.clk(clk),.rst_n(rst_n),.clk_rd(clk),.clk_ws(clk),.clk_macro({6{clk}}),
  .read_v(rv),.read_addr(ra),.read_data(qr),.read_return(vr),.write_v(wvr),.write_addr(war),.write_data(wdr));
 integer n=0,bad=0,i,seed=32'h1106,x;
 always @(posedge clk)begin
  wv1<=wv;wa1<=wa;wd1<=wd;
  x=$random(seed);
  rv<=rst_n?x[5:0]:6'd0;
  for(i=0;i<6;i=i+1)begin x=$random(seed);ra[i*9+:9]<={3'd0,1'b0,x[1:0],x[4:2]};end
  x=$random(seed);
  wv<=rst_n&&x[0];
  wa<={3'd0,1'b0,x[2:1],x[5:3]};
  wd<=$random(seed);
  if(rst_n)for(i=0;i<6;i=i+1)begin
   if(vd[i]===1'b1)begin
    n=n+1;
    if(vr[i]!==1'b1||qd[i*32+:32]!==qr[i*32+:32])begin bad=bad+1;if(bad<4)$display("MISMATCH t=%0t col=%0d %h %h",$time,i,qd[i*32+:32],qr[i*32+:32]);end
   end else if(vr[i]===1'b1)begin bad=bad+1;if(bad<4)$display("MISMATCH valid t=%0t col=%0d",$time,i);end
  end
 end
 initial begin
  #105 rst_n=1;
  #4000000;
  $display("XEQ W=%0d D=%0d MC=%0d MW=%0d checks=%0d bad=%0d %s",`W,`D,`MC,`MW,n,bad,(bad==0&&n>100000)?"PASS":"FAIL");
  $finish;
 end
endmodule
