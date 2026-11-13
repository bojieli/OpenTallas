`timescale 1ns/1ps
// R5 conservative H8 candidate: serialize each RT4/PWORDS2 input into two
// original RT2/PWORDS2 loads, preserving the signed H16 head macro unchanged.
// Valid SVC calendar: P loads every2clocks, no other load in the replay slot.
// Generic inter-job ILV Q/P load collisions need an explicitly priced queue;
// they are detected here. The original scalar32-term reduction is unchanged.
module ot_s81c_h8_rt2_load (
 input wire clk,rst_n,ld_v,ld_mode,input wire[2:0]ld_bank,input wire[7:0]ld_grp,
 input wire[1023:0]ld_w,input wire ld_w2v,
 output wire out_v,out_mode,
 output wire[2:0]out_bank,output wire[7:0]out_grp,output wire[1023:0]out_w,
 output wire out_w2v,output reg fault
);
 reg pending;reg[511:0]second;reg[2:0]bank;reg[7:0]group_second;
 // One H8word contains4rows×8heads. Expand to two old H16words, each2rows×16heads.
 // Only original head macros0..7 are instantiated; empty upper-head fields stayinternal.
 function automatic[1023:0]expand(input[511:0]x);
  expand=0;
  for(integer row=0;row<4;row++)for(integer h=0;h<8;h++)
   expand[16*(16*row+h)+:16]=x[16*(8*row+h)+:16];
 endfunction
 wire bad_group=ld_mode&&(ld_grp[0]||ld_grp>8'd6);
 assign out_v=pending||(ld_v&&!bad_group);
 assign out_mode=pending||ld_mode;
 assign out_bank=pending?bank:ld_bank;
 assign out_grp=pending?group_second:(ld_mode?{ld_grp[6:0],1'b0}:ld_grp);
 assign out_w=pending?expand(second):(ld_mode?expand(ld_w[511:0]):ld_w);
 // Every live H8word expands into two complete old2row words. Invalid tail
 // rows remain masked by the native V-row pad bits, as before.
 assign out_w2v=(pending||ld_mode)?1'b1:ld_w2v;
 always@(posedge clk)begin
  if(!rst_n)begin pending<=0;fault<=0;end
  else begin
   if(ld_v&&(pending||bad_group))fault<=1;
   pending<=!pending&&ld_v&&ld_mode&&!bad_group&&ld_w2v;
  end
  if(ld_v&&ld_mode&&!pending)begin second<=ld_w[1023:512];bank<=ld_bank;group_second<={ld_grp[6:0],1'b0}+8'd2;end
 end
endmodule

// PAIR (HARD-S81-SVC-1 11-13, COORD ruling after the band place + GRT; 0 = as built, names unchanged):
//   1 = the reset and the load word are registered once per CORE PAIR inside the tile: four copies of the CTLA sender
//       (u_load_stage for cores 0-1, g_pr[1..3].u_ls for cores 2-3 / 4-5 / 6-7; same inputs, same edge, so NO cycle
//       moves) and one reset register per pair in front of that pair's sender and cores, plus one in front of
//       u_expand.  Every consumer sees the reset exactly one edge later than as built (rst_n is held >= 64 clk).
//       Outline, pins and the signed head macro are unchanged.
//   2 = bench negative control: the sender of pair 3 never sees a load.
module ot_s81c_attn_tile_hc_h8_rt2 #(parameter integer PAIR = 0) (
 input wire clk,rst_n,ld_v,ld_mode,input wire[2:0]ld_bank,input wire[7:0]ld_grp,
 input wire[1023:0]ld_w,input wire ld_w2v,iv,input wire[2:0]ibank,input wire[575:0]ib,
 output wire ov,output wire[255:0]oy,output wire[7:0]oflt
);
 wire rx;wire[3:0]rq;
 generate if(PAIR!=0)begin:g_rst
  (* keep = "true" *) reg re;
  (* keep = "true" *) reg[3:0]rp;
  always@(posedge clk)begin re<=rst_n;rp<={4{rst_n}};end
  assign rx=re;assign rq=rp;
 end else begin:g_rst0
  assign rx=rst_n;assign rq={4{rst_n}};
 end endgenerate
 wire av,am,a2,af;wire[2:0]ab;wire[7:0]ag;wire[1023:0]aw;
 ot_s81c_h8_rt2_load u_expand(.clk(clk),.rst_n(rx),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.out_v(av),.out_mode(am),.out_bank(ab),.out_grp(ag),.out_w(aw),.out_w2v(a2),.fault(af));
 wire[3:0]sv,sm,s2;wire[4*3-1:0]sb;wire[4*8-1:0]sg;wire[4*1024-1:0]sw;
 // Exactly the existing CTLA sender. No modification of the signed head macro.
 ot_s81c_hcore_load_stage u_load_stage(.clk(clk),.rst_n(rq[0]),.ld_v(av),.ld_mode(am),.ld_bank(ab),.ld_grp(ag),.ld_w(aw),.ld_w2v(a2),.out_v(sv[0]),.out_mode(sm[0]),.out_bank(sb[2:0]),.out_grp(sg[7:0]),.out_w(sw[1023:0]),.out_w2v(s2[0]));
 for(genvar p=1;p<4;p++)begin:g_pr
  if(PAIR!=0)begin:g_c
   (* keep = "true" *) ot_s81c_hcore_load_stage u_ls(.clk(clk),.rst_n(rq[p]),.ld_v((PAIR==2&&p==3)?1'b0:av),.ld_mode(am),.ld_bank(ab),.ld_grp(ag),.ld_w(aw),.ld_w2v(a2),.out_v(sv[p]),.out_mode(sm[p]),.out_bank(sb[3*p+:3]),.out_grp(sg[8*p+:8]),.out_w(sw[1024*p+:1024]),.out_w2v(s2[p]));
  end else begin:g_s
   assign sv[p]=sv[0];assign sm[p]=sm[0];assign s2[p]=s2[0];assign sb[3*p+:3]=sb[2:0];assign sg[8*p+:8]=sg[7:0];assign sw[1024*p+:1024]=sw[1023:0];
  end
 end
 wire[7:0]hv,hf;
 for(genvar g=0;g<8;g++)begin:g_h
  wire[63:0]wp;
  for(genvar w=0;w<2;w++)for(genvar j=0;j<2;j++)begin:g_wp
   assign wp[16*(2*w+j)+:16]=sw[1024*(g/2)+w*512+16*(16*j+g)+:16];
  end
  ot_s81c_attn_hcore u_c(.clk(clk),.rst_n(rq[g/2]),.gid(8'(g)),.ld_v(sv[g/2]),.ld_mode(sm[g/2]),.ld_bank(sb[3*(g/2)+:3]),.ld_grp(sg[8*(g/2)+:8]),.ld_w(sw[1024*(g/2)+:512]),.ld_wp(wp),.ld_w2v(s2[g/2]),.iv(iv),.ibank(ibank),.ib(ib),.ov(hv[g]),.oy(oy[32*g+:32]),.oflt(hf[g]));
 end
 assign ov=hv[0];assign oflt=hf|{8{af}};
endmodule
