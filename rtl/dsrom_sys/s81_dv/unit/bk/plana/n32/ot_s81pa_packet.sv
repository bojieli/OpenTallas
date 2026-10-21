`timescale 1ns/1ps
// Consumer-local copy of the original merger's state, at its EXISTING edge.
// state_next is the actual producer next-state expression, not current state.
(* keep_hierarchy="yes" *)
module ot_s81pa_packet #(parameter integer LO=0,SW=24,ID=0)(
 input wire clk,input wire[4:0]rst_n,input wire[52:0]state_next,
 input wire[1:0]selector_next,input wire[4*358-1:0]heads,
 output reg[SW-1:0]out);
 localparam[52:0]INIT=53'd65536; // original done_pend=1; other packet-control fields0
 (* keep *)reg[52:0]state;
 // [ELEM-BKG] eight kept same-edge copies of tsel (was one register, 100/51 loads); bit b uses copy b%8
 wire[15:0]tsel_k;
 generate for(genvar k=0;k<8;k=k+1)begin:g_tsel
  ot_s81pa_copy #(.W(2),.ID(4096+8*ID+k))u_t(.clk(clk),.d(selector_next),.q(tsel_k[2*k+:2]));
 end endgenerate
 generate for(genvar c=0;c<4;c=c+1)begin:g_state
  localparam integer B=c*16,W=(53-B<16)?53-B:16;
  always @(posedge clk or negedge rst_n[c])
   if(!rst_n[c])state[B+:W]<=INIT[B+:W];
   else state[B+:W]<=state_next[B+:W];
 end endgenerate
 wire[3:0]ready;wire[11:0]counts;wire[7:0]tag;wire[4:0]flt,fltr;
 wire[1:0]rep,pc,cq;wire done,rn,ovf;wire[9:0]cnt;
 assign{ready,counts,tag,flt,fltr,rep,done,pc,rn,cq,cnt,ovf}=state;
 reg[357:0]hd;reg[2:0]count;
 always @*begin
  hd=0;count=0;
  for(integer q=0;q<4;q=q+1)begin
   for(integer b=0;b<358;b=b+1)if(tsel_k[2*(b%8)+:2]==2'(q))hd[b]=heads[358*q+b];
   for(integer b=0;b<3;b=b+1)if(tsel_k[2*((b+5)%8)+:2]==2'(q))count[b]=counts[3*q+b];
  end
 end
 wire[4:0]fresh=flt&~fltr;
 wire take=(pc==0)&&!(|fresh)&&(rep==0)&&!done&&(count!=0);
 reg write;reg[511:0]word;
 always @*begin
  write=0;word=0;
  if(pc==0)begin
   if(|fresh)begin write=1;word={4'd5,tag,484'd0,flt,11'd0};end
   else if(rep!=0&&(&ready))begin write=1;word={4'd7,tag,499'd0,rn};end
   else if(take)begin write=1;word={4'd3,tag,145'd0,hd[352],cq,hd[351:336],hd[335:320],hd[319:0]};end
   else if(done&&(&ready))begin write=1;word={4'd4,tag,484'd0,flt,ovf,cnt};end
  end
 end
 always @(posedge clk or negedge rst_n[4])
  if(!rst_n[4])out<=0;else if(write)out<=word[LO+:SW];
endmodule

// The parent's existing4-edge run is REPLACED for this one child. This consumes
// raw rst_n_core, never an already landed lpr_core. Thus parent4 + child2 stays6.
(* keep_hierarchy="yes" *)
module ot_s81pa_parent_rst #(parameter integer NR=448, N1=(NR+31)/32)(
 input wire clk,rst_raw,output wire[NR-1:0]rst_profile);
 wire s0;wire[N1-1:0]s1;wire[NR-1:0]s2;
 ot_pl_land_rst_copy #(.ID(800000))u0(.ck(clk),.d(rst_raw),.q(s0));
 generate for(genvar k=0;k<N1;k=k+1)begin:g1
  ot_pl_land_rst_copy #(.ID(800001+k))u(.ck(clk),.d(s0),.q(s1[k]));
 end
 for(genvar k=0;k<NR;k=k+1)begin:g2
  ot_pl_land_rst_copy #(.ID(801000+k))u2(.ck(clk),.d(s1[k/32]),.q(s2[k]));
  ot_pl_land_rst_copy #(.ID(802000+k))u3(.ck(clk),.d(s2[k]),.q(rst_profile[k]));
 end endgenerate
`ifndef SYNTHESIS
 initial if(N1>32||NR<1)$fatal(1,"parent reset profile out of bounded4stage range");
`endif
endmodule

(* keep_hierarchy="yes" *)
module ot_s81pa_rst_leaf #(parameter integer ID=0)(input wire clk,raw,output wire q);
 (* keep *)reg[1:0]s;
 always @(posedge clk or negedge raw)if(!raw)s<=0;else s<={s[0],1'b1};
 assign q=s[1];
endmodule
