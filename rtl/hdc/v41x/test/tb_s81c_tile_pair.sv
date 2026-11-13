`timescale 1ns/1ps
// HARD-S81-SVC-1 (11-13): the H8 RT2 tile as built (PAIR 0) vs the per-core-pair form (PAIR 1) vs its negative control
// (PAIR 2), on the production H8 block schedule of tb_s81c_h8_rt2 (eight Q head loads, QK beats, four paired P loads,
// P.V issues) with random words and a warm reset.  The as-built copy gets the reset one edge later (the pair form
// registers the reset once in front of every consumer).  Every cycle ov / oflt must be equal, and oy whenever ov.
module tb_s81c_tile_pair;
 reg clk=0;always#0.5 clk=~clk;
 reg rst_n=0,rst_d=0,ld_v=0,ld_mode=0,ld_w2v=0,iv=0;
 reg[2:0]ld_bank=0,ibank=0;reg[7:0]ld_grp=0;
 reg[1023:0]ld_w=0;reg[575:0]ib=0;
 always@(posedge clk)rst_d<=rst_n;
 wire lo;wire[255:0]ly;wire[7:0]lf;
 reg[4:0]ro3=0;reg[255:0]ry3[0:4];reg[7:0]rf3[0:4];integer lerr=0;
 integer ri;
 always@(posedge clk)begin
  ro3<={ro3[3:0],ro};ry3[0]<=ry;rf3[0]<=rf;
  for(ri=1;ri<5;ri=ri+1)begin ry3[ri]<=ry3[ri-1];rf3[ri]<=rf3[ri-1];end
 end
 wire ro,po,mo,co,so;wire[255:0]ry,py,my,cy,sy;wire[7:0]rf,pf,mf,cf,sf;
 reg ro1=0;reg[255:0]ry1=0;reg[7:0]rf1=0;integer serr=0;
 always@(posedge clk)begin ro1<=ro;ry1<=ry;rf1<=rf;end
 ot_s81c_attn_tile_hc_h8_rt2 #(.PAIR(0)) u_ref(.clk(clk),.rst_n(rst_d),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(ro),.oy(ry),.oflt(rf));
 ot_s81c_attn_tile_hc_h8_rt2 #(.PAIR(1)) u_pair(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(po),.oy(py),.oflt(pf));
 ot_s81c_attn_tile_hc_h8_rt2 #(.PAIR(3)) u_core(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(co),.oy(cy),.oflt(cf));
 ot_s81c_attn_tile_hc_h8_rt2 #(.PAIR(4)) u_stage(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(so),.oy(sy),.oflt(sf));
 ot_s81c_attn_tile_hc_h8_rt2 #(.PAIR(5)) u_reach(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(lo),.oy(ly),.oflt(lf));
 ot_s81c_attn_tile_hc_h8_rt2 #(.PAIR(2)) u_mut(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(mo),.oy(my),.oflt(mf));
 reg[31:0]xs;integer cyc=0,err=0,merr=0,nov=0,nz=0,seed=1,ncyc=16000,qk_first=16,phase,blk,nrst=0;
 function automatic[31:0]rnd(input integer dummy);reg[31:0]x;begin x=xs;x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);xs=x;rnd=x;end endfunction
 initial begin
  void'($value$plusargs("seed=%d",seed));void'($value$plusargs("cycles=%d",ncyc));
  xs=32'h9e3779b9^(seed*32'h85ebca6b);
 end
 always@(posedge clk)begin
  cyc<=cyc+1;
  if(cyc==3)rst_n<=1;
  phase=(cyc>=60)?(cyc-60)%160:-1;blk=(cyc>=60)?(cyc-60)/160:0;
  // warm resets in the middle of the stream (different phases)
  if(cyc==941||cyc==4107||cyc==9333)begin rst_n<=0;nrst<=nrst+1;end
  if(cyc==951||cyc==4109||cyc==9390)rst_n<=1;
  ld_v<=((phase>=0&&phase<8)||(phase>=80&&phase<=86&&phase%2==0));
  ld_mode<=phase>=80&&phase<=86;
  ld_w2v<=1;
  ld_bank<=3'(blk%5);ld_grp<=8'(phase>=80?phase-80:phase);
  // Exercise the expander sticky-fault pipeline as well as core data.
  if(cyc==700||cyc==5000)begin ld_v<=1;ld_mode<=1;ld_grp<=8'd1;end
  for(integer i=0;i<32;i++)ld_w[32*i+:32]<=rnd(0);
  iv<=((phase>=qk_first&&phase<qk_first+8)||(phase>=86&&phase<=93))&&blk!=5;
  ibank<=3'(blk%5);
  for(integer i=0;i<18;i++)ib[32*i+:32]<=rnd(0);
  if(cyc>12)begin
   if(ro!==po||rf!==pf||(ro&&ry!==py)||ro!==co||rf!==cf||(ro&&ry!==cy))begin err++;if(err<=5)$display("TILE_PAIR mismatch cyc%0d ov%b/%b f%02x/%02x",cyc,ro,po,rf,pf);end
   if(ro!==mo||rf!==mf||(ro&&ry!==my))merr++;
   // PAIR 4: the as-built outputs one edge later
   if(ro1!==so||rf1!==sf||(ro1&&ry1!==sy))begin serr++;if(serr<=5)$display("TILE_STAGE mismatch cyc%0d ov%b/%b f%02x/%02x",cyc,ro1,so,rf1,sf);end
   if(ro3[4]!==lo||rf3[4]!==lf||(ro3[4]&&ry3[4]!==ly))begin lerr++;if(lerr<=5)$display("TILE_REACH mismatch cyc%0d ov%b/%b f%02x/%02x",cyc,ro3[4],lo,rf3[4],lf);end
   if(ro)begin nov++;if(ry!=0)nz++;end
  end
  if(cyc==ncyc)begin
   $display("TILE_PAIR seed=%0d cycles=%0d warm_resets=%0d ov=%0d nonzero=%0d mismatches=%0d stage_mismatches=%0d reach_mismatches=%0d mutant_mismatches=%0d",seed,ncyc,nrst,nov,nz,err,serr,lerr,merr);
   if(err==0&&serr==0&&lerr==0&&nov>1000&&nz>100&&merr>0)$display("TILE_PAIR PASS");else $display("TILE_PAIR FAIL");$finish;
  end
 end
endmodule
