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
//   4 = as 3 plus one input register stage PER CORE in front of that core's sender and issue pins (load line, load
//       group / valid, iv / ibank / ib): the unregistered CTLA controls (out_grp / out_w2v lead the data by one edge)
//       now start at a register beside the core and keep their one-edge lead.  Every core input moves by exactly one
//       edge, so the tile's outputs leave ONE EDGE LATER with unchanged internal timing (the parent adds 1 to its tags);
//       the per-core reset is registered twice (one edge later than at 3) so reset and stream stay aligned.
//   3 = as 1 but once per CORE (8 senders, 8 reset registers): the core takes ld_w / ld_wp on its west face, so each
//       sender belongs in its own core's west street (band kit v4: per-pair senders had to cross a core).
module ot_s81c_attn_tile_hc_h8_rt2 #(parameter integer PAIR = 0) (
 input wire clk,rst_n,ld_v,ld_mode,input wire[2:0]ld_bank,input wire[7:0]ld_grp,
 input wire[1023:0]ld_w,input wire ld_w2v,iv,input wire[2:0]ibank,input wire[575:0]ib,
 output wire ov,output wire[255:0]oy,output wire[7:0]oflt
);
 // PAIR 5: five per-core input stages, placed along the source-to-core path.
 // All input lanes and the local reset move together; outputs leave five edges later.
 localparam integer INPUT_STAGES=(PAIR==5)?5:1;
 localparam integer NG=(PAIR>=3)?8:4;      // sender / reset groups
 wire rx;wire[7:0]rq;
 generate if(PAIR!=0)begin:g_rst
  (* keep = "true" *) reg [INPUT_STAGES-1:0] re;
  (* keep = "true" *) reg[NG-1:0]rp;
  integer ri;
  always@(posedge clk)begin
   re[0]<=rst_n;
   for(ri=1;ri<INPUT_STAGES;ri=ri+1)re[ri]<=re[ri-1];
   rp<={NG{(PAIR>=4)?re[INPUT_STAGES-1]:rst_n}};
  end
  assign rx=re[0];assign rq=8'(rp);
 end else begin:g_rst0
  assign rx=rst_n;assign rq={8{rst_n}};
 end endgenerate
 wire av,am,a2,af;wire[2:0]ab;wire[7:0]ag;wire[1023:0]aw;
 ot_s81c_h8_rt2_load u_expand(.clk(clk),.rst_n(rx),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.out_v(av),.out_mode(am),.out_bank(ab),.out_grp(ag),.out_w(aw),.out_w2v(a2),.fault(af));
 wire[7:0]sv,sm,s2;wire[8*3-1:0]sb;wire[8*8-1:0]sg;wire[8*1024-1:0]sw;
 // PAIR 4: per-core input stage (xv.. = the sender inputs of group p; yv / yb / yi = the issue pins of core p)
 wire[7:0]xv,xm,x2,yv;wire[8*3-1:0]xb,yb;wire[8*8-1:0]xg;wire[8*1024-1:0]xw;wire[8*576-1:0]yi;
 for(genvar p=0;p<8;p++)begin:g_in
  if(PAIR>=4)begin:g_r
   (* keep = "true" *) reg [INPUT_STAGES-1:0] qv,qm,q2,jv;
   (* keep = "true" *) reg[2:0]qb[0:INPUT_STAGES-1],jb[0:INPUT_STAGES-1];
   (* keep = "true" *) reg[7:0]qg[0:INPUT_STAGES-1];
   (* keep = "true" *) reg[1023:0]qw[0:INPUT_STAGES-1];
   (* keep = "true" *) reg[575:0]ji[0:INPUT_STAGES-1];
   integer si;
   always@(posedge clk)begin
    qv[0]<=av;jv[0]<=iv;qm[0]<=am;q2[0]<=a2;qb[0]<=ab;qg[0]<=ag;qw[0]<=aw;jb[0]<=ibank;ji[0]<=ib;
    for(si=1;si<INPUT_STAGES;si=si+1)begin
     qv[si]<=qv[si-1];jv[si]<=jv[si-1];qm[si]<=qm[si-1];q2[si]<=q2[si-1];
     qb[si]<=qb[si-1];qg[si]<=qg[si-1];qw[si]<=qw[si-1];jb[si]<=jb[si-1];ji[si]<=ji[si-1];
    end
   end
   assign xv[p]=qv[INPUT_STAGES-1];assign xm[p]=qm[INPUT_STAGES-1];assign x2[p]=q2[INPUT_STAGES-1];
   assign xb[3*p+:3]=qb[INPUT_STAGES-1];assign xg[8*p+:8]=qg[INPUT_STAGES-1];assign xw[1024*p+:1024]=qw[INPUT_STAGES-1];
   assign yv[p]=jv[INPUT_STAGES-1];assign yb[3*p+:3]=jb[INPUT_STAGES-1];assign yi[576*p+:576]=ji[INPUT_STAGES-1];
  end else begin:g_w
   assign xv[p]=av;assign xm[p]=am;assign x2[p]=a2;assign xb[3*p+:3]=ab;assign xg[8*p+:8]=ag;assign xw[1024*p+:1024]=aw;
   assign yv[p]=iv;assign yb[3*p+:3]=ibank;assign yi[576*p+:576]=ib;
  end
 end
 // Exactly the existing CTLA sender. No modification of the signed head macro.
 ot_s81c_hcore_load_stage u_load_stage(.clk(clk),.rst_n(rq[0]),.ld_v(xv[0]),.ld_mode(xm[0]),.ld_bank(xb[2:0]),.ld_grp(xg[7:0]),.ld_w(xw[1023:0]),.ld_w2v(x2[0]),.out_v(sv[0]),.out_mode(sm[0]),.out_bank(sb[2:0]),.out_grp(sg[7:0]),.out_w(sw[1023:0]),.out_w2v(s2[0]));
 for(genvar p=1;p<8;p++)begin:g_pr
  if(PAIR!=0&&p<NG)begin:g_c
   (* keep = "true" *) ot_s81c_hcore_load_stage u_ls(.clk(clk),.rst_n(rq[p]),.ld_v((PAIR==2&&p==3)?1'b0:xv[p]),.ld_mode(xm[p]),.ld_bank(xb[3*p+:3]),.ld_grp(xg[8*p+:8]),.ld_w(xw[1024*p+:1024]),.ld_w2v(x2[p]),.out_v(sv[p]),.out_mode(sm[p]),.out_bank(sb[3*p+:3]),.out_grp(sg[8*p+:8]),.out_w(sw[1024*p+:1024]),.out_w2v(s2[p]));
  end else begin:g_s
   assign sv[p]=sv[0];assign sm[p]=sm[0];assign s2[p]=s2[0];assign sb[3*p+:3]=sb[2:0];assign sg[8*p+:8]=sg[7:0];assign sw[1024*p+:1024]=sw[1023:0];
  end
 end
 wire[7:0]hv,hf;
 for(genvar g=0;g<8;g++)begin:g_h
  localparam integer GI=(PAIR>=3)?g:g/2;   // this core's sender / reset group
  wire[63:0]wp;
  for(genvar w=0;w<2;w++)for(genvar j=0;j<2;j++)begin:g_wp
   assign wp[16*(2*w+j)+:16]=sw[1024*GI+w*512+16*(16*j+g)+:16];
  end
  ot_s81c_attn_hcore u_c(.clk(clk),.rst_n(rq[GI]),.gid(8'(g)),.ld_v(sv[GI]),.ld_mode(sm[GI]),.ld_bank(sb[3*GI+:3]),.ld_grp(sg[8*GI+:8]),.ld_w(sw[1024*GI+:512]),.ld_wp(wp),.ld_w2v(s2[GI]),.iv(yv[g]),.ibank(yb[3*g+:3]),.ib(yi[576*g+:576]),.ov(hv[g]),.oy(oy[32*g+:32]),.oflt(hf[g]));
 end
  wire af_out;
  generate if(PAIR>=4)begin:g_af
   reg[INPUT_STAGES-1:0]aq;
   integer ai;
   always@(posedge clk)begin
    aq[0]<=af;
    for(ai=1;ai<INPUT_STAGES;ai=ai+1)aq[ai]<=aq[ai-1];
   end
   assign af_out=aq[INPUT_STAGES-1];
  end else begin:g_af0
   assign af_out=af;
  end endgenerate
  assign ov=hv[0];assign oflt=hf|{8{af_out}};
endmodule
