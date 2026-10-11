`timescale 1ns/1ps
// Actual TU PHY emits pulses, no ready: credit-qualified protected ingress.
// Preserve full545bit record. Source SWCRED must be <=DEPTH with actual pop
// returns; an out-of-contract arrival faults rather than overwriting debt.
// Full-rate protected reads reserve HEAD response slots before issuing.
module ot_hbm_retry_phy_ingress #(
 parameter W=545,SW=12,EW=16,DEPTH=256,HEAD=8,NOEPOCH=0, // NOEPOCH: see ot_hbm_replay_sram (sys-takeover)
 parameter MUXREG=0, // redesign-ds: ot_hbm_replay_sram MUXREG (+1 read edge; HEAD response slots reserved before issue)
 // HWU (hardcore-1010 grp C, 2026-10-10, default 0; on with the TU FB line): the 8 x 545-b head entries are written on
 // every read response (enable = ov and the registered tail only); the check (ue, session/epoch compare, overflow)
 // only decides whether the tail advances or the port faults.  Route turetryphy-fb-ea354a5b2-b post-CTS TT -482:
 // ses_q -> re != session (24 b) -> 4,360 head D enables.  A rejected response lands in the slot past the tail, which
 // is never valid (the tail does not advance and the fault is sticky), so the delivered stream is unchanged.
 parameter HWU=0,
 // HREP (tu-retry-1011, default 0): the head read pointer is replicated per RS-bit slice of the record (keep_hierarchy
 // copies of one next-state, ot_hbm_tu_rep_q), so each copy selects RS bits of the 8:1 head mux.  cp-9e7cf26ca-b
 // post-CTS: u_ingress.hp -> 545 x 8:1 select buffer tree (510 ps) -> skid m0/m1 -41 ps.  Cycle-exact (copies = hp).
 parameter HREP=0, RS=64,
 parameter HW=$clog2(HEAD),CW=$clog2(HEAD)+1
)(
 input wire clk,rst_n,input wire[EW-1:0]session,
 input wire in_valid,input wire[W-1:0]in_data,output wire in_ready,
 output wire out_valid,input wire out_ready,output wire[W-1:0]out_data,
 output reg fault,output wire[SW-1:0]debt
);
 reg[SW-1:0]wseq,issued,consumed,committed;
 reg[HW-1:0]hp,ht;
 reg[CW-1:0]hn,reserved;
 reg[W-1:0]head[0:HEAD-1];
 assign debt=wseq-consumed;
 assign in_ready=!fault && debt<DEPTH;
 assign out_valid=!fault && hn!=0;
 wire push=in_valid && in_ready;
 wire pop=out_valid && out_ready;
 generate if(HREP)begin:g_hrep
  localparam integer NS=(W+RS-1)/RS;
`ifdef OT_TU_HREP_MUT
  wire[HW-1:0]hp_n=hp;                   // negative control: the copies never advance with a pop
`else
  wire[HW-1:0]hp_n=pop ? hp+1'b1 : hp;   // = hp's update (pop implies !fault)
`endif
  for(genvar k=0;k<NS;k=k+1)begin:g_s
   localparam integer LO=k*RS, WD=(W-LO<RS) ? W-LO : RS;
   wire[HW-1:0]hq;
   ot_hbm_tu_rep_q #(.W(HW)) u_rep(.clk(clk),.rst_n(rst_n),.d(hp_n),.q(hq));
   wire[W-1:0]hd=head[hq];
   assign out_data[LO+:WD]=hd[LO+:WD];
  end
 end else begin:g_hdir
 assign out_data=head[hp];
 end endgenerate
 wire fetch=!fault && issued!=committed && reserved<HEAD;
 wire ov,ce,ue;wire[W-1:0]rd;wire[SW-1:0]rs;wire[EW-1:0]re;
 ot_hbm_replay_sram #(.W(W),.SW(SW),.EW(EW),.DEPTH(DEPTH),.NOEPOCH(NOEPOCH),.MUXREG(MUXREG)) u_memory(
 .clk(clk),.rst_n(rst_n),.w_valid(push),.w_data(in_data),.w_seq(wseq),.w_session(session),
 .r_valid(fetch),.r_seq(issued),.r_session(session),.o_valid(ov),.o_data(rd),.o_seq(rs),.o_session(re),.o_ce(ce),.o_ue(ue));
 always@(posedge clk or negedge rst_n)begin
 if(!rst_n)begin wseq<=0;issued<=0;consumed<=0;committed<=0;hp<=0;ht<=0;hn<=0;reserved<=0;fault<=0;end
 else if(!fault)begin
 committed<=wseq;
 if(push)wseq<=wseq+1'b1;
 if(fetch)issued<=issued+1'b1;
 if(pop)begin consumed<=consumed+1'b1;hp<=hp+1'b1;end
 reserved<=reserved+(fetch?1'b1:1'b0)-(pop?1'b1:1'b0);
 hn<=hn+(ov?1'b1:1'b0)-(pop?1'b1:1'b0);
 if(ov)begin
 if(ue || (!NOEPOCH && re!=session) || hn>=HEAD)fault<=1;
 else begin if(!HWU)head[ht]<=rd;ht<=ht+1'b1;end end
 if(in_valid && !in_ready)fault<=1;
 end end
 // HWU: the head data path written from registered state only (outside the reset / fault conditions)
`ifdef OT_TU_HWU_MUT
 always@(posedge clk) if(HWU && ov)head[ht+1'b1]<=rd;   // negative control: the response lands one slot late
`else
 always@(posedge clk) if(HWU && ov)head[ht]<=rd;
`endif
 initial if(HEAD<6 || (HEAD&(HEAD-1)))$fatal(1,"insufficient read-response reservations");
endmodule
