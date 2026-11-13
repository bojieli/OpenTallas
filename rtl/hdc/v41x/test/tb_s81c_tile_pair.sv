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
 wire ro,po,mo;wire[255:0]ry,py,my;wire[7:0]rf,pf,mf;
 ot_s81c_attn_tile_hc_h8_rt2 #(.PAIR(0)) u_ref(.clk(clk),.rst_n(rst_d),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(ro),.oy(ry),.oflt(rf));
 ot_s81c_attn_tile_hc_h8_rt2 #(.PAIR(1)) u_pair(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(po),.oy(py),.oflt(pf));
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
  for(integer i=0;i<32;i++)ld_w[32*i+:32]<=rnd(0);
  iv<=((phase>=qk_first&&phase<qk_first+8)||(phase>=86&&phase<=93))&&blk!=5;
  ibank<=3'(blk%5);
  for(integer i=0;i<18;i++)ib[32*i+:32]<=rnd(0);
  if(cyc>12)begin
   if(ro!==po||rf!==pf||(ro&&ry!==py))begin err++;if(err<=5)$display("TILE_PAIR mismatch cyc%0d ov%b/%b f%02x/%02x",cyc,ro,po,rf,pf);end
   if(ro!==mo||rf!==mf||(ro&&ry!==my))merr++;
   if(ro)begin nov++;if(ry!=0)nz++;end
  end
  if(cyc==ncyc)begin
   $display("TILE_PAIR seed=%0d cycles=%0d warm_resets=%0d ov=%0d nonzero=%0d mismatches=%0d mutant_mismatches=%0d",seed,ncyc,nrst,nov,nz,err,merr);
   if(err==0&&nov>1000&&nz>100&&merr>0)$display("TILE_PAIR PASS");else $display("TILE_PAIR FAIL");$finish;
  end
 end
endmodule
