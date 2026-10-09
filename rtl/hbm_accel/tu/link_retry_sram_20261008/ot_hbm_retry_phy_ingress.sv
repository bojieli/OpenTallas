`timescale 1ns/1ps
// Actual TU PHY emits pulses, no ready: credit-qualified protected ingress.
// Preserve full545bit record. Source SWCRED must be <=DEPTH with actual pop
// returns; an out-of-contract arrival faults rather than overwriting debt.
// Full-rate protected reads reserve HEAD response slots before issuing.
module ot_hbm_retry_phy_ingress #(
 parameter W=545,SW=12,EW=16,DEPTH=256,HEAD=8,NOEPOCH=0, // NOEPOCH: see ot_hbm_replay_sram (sys-takeover)
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
 assign out_data=head[hp];
 wire push=in_valid && in_ready;
 wire pop=out_valid && out_ready;
 wire fetch=!fault && issued!=committed && reserved<HEAD;
 wire ov,ce,ue;wire[W-1:0]rd;wire[SW-1:0]rs;wire[EW-1:0]re;
 ot_hbm_replay_sram #(.W(W),.SW(SW),.EW(EW),.DEPTH(DEPTH),.NOEPOCH(NOEPOCH)) u_memory(
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
 else begin head[ht]<=rd;ht<=ht+1'b1;end end
 if(in_valid && !in_ready)fault<=1;
 end end
 initial if(HEAD<6 || (HEAD&(HEAD-1)))$fatal(1,"insufficient read-response reservations");
endmodule
