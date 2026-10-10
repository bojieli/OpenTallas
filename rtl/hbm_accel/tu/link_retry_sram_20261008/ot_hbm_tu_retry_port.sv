`timescale 1ns/1ps
// TU545 boundary over vendor FEC. All ports are stream-clock synchronous.
// Caller binds rx_consumed to ACTUAL TU landing-FIFO pop, not FEC acceptance.
// Receiver landing storage belongs to TU; no behavioral stand-in here.
// PHY input/output are elastic pin interfaces with conserved landing credits.
// rst_n/link_up release must come from the region reset/training sequencer.
// Session changes on coordinated link reset; old-session frames are dropped.
module ot_hbm_tu_retry_port #(
 parameter ENABLE=0, W=545, SW=12, EW=16, DEPTH=512, CAPACITY=256,
 parameter CW=$clog2(CAPACITY)+2, TIMEOUT=2048, MAX_RETRY=8,
 // NOEPOCH=1 (sys-takeover 2026-10-09, opt-in; review S4/S5): no session/epoch identity and no sequence in the stored
 // record or its checks; SECDED covers the replay payload only.  Go-back-N sequence numbers on the link are unchanged.
 parameter NOEPOCH=0,
 parameter PIPE_FIX=0, // cont-takeover: HEAD_FREE in the retry SRAM controller
 parameter SESREG=0,    // redesign-ds: registered feedback session match (fb_m) + per-slot replay session flags
 parameter MUXREG=0     // redesign-ds: replay SRAM registered bank select (ot_hbm_replay_sram MUXREG)
)(
 input wire clk,rst_n,link_up,input wire[EW-1:0] session,
 input wire in_valid,output wire in_ready,input wire[W-1:0] in_data,
 output wire tx_valid,input wire tx_ready,output wire[W-1:0] tx_data,
 output wire[SW-1:0] tx_seq,output wire[EW-1:0] tx_session,
 input wire rx_valid,output wire rx_ready,input wire rx_ue,
 input wire[W-1:0] rx_data,input wire[SW-1:0] rx_seq,input wire[EW-1:0] rx_session,
 output wire out_valid,input wire out_ready,output wire[W-1:0] out_data,
 input wire rx_consumed,
 output wire[SW-1:0] ack_seq,output wire ack_nak,output wire[EW-1:0] ack_session,
 output wire[CW-1:0] ack_pop,
 input wire fb_valid,fb_good,fb_nak,input wire[SW-1:0] fb_seq,
 input wire[EW-1:0] fb_session,input wire[CW-1:0] fb_pop,input wire fb_m,
 output wire fault,output wire[SW-1:0] retained,
 output wire[CW-1:0] available,output wire[CW-1:0] rx_debt,
 output wire[31:0] replay_count
);
 wire run=rst_n && link_up;
 reg[CW-1:0] credits,pop_seen,pop_total,rx_owned;
 reg credit_fault;
 wire[CW-1:0] pop_delta=fb_pop-pop_seen;
 wire fb_current=fb_valid && fb_good && (NOEPOCH || (SESREG ? fb_m : fb_session==session));
 wire pop_advance=fb_current && pop_delta!=0 && !pop_delta[CW-1];
 wire[CW-1:0] tx_owned=CAPACITY-credits;
 wire return_ok=pop_advance && pop_delta<=tx_owned;
 wire core_ready,core_ov,core_fault,core_tv,core_rr;
 wire allow_new=!ENABLE || credits!=0;
 wire put=in_valid && in_ready;
 wire landed=out_valid && out_ready;
 wire consumed=rx_consumed && rx_owned!=0;
 wire consumer_ready=out_ready && (!ENABLE || rx_owned<CAPACITY);
 assign in_ready=run && !credit_fault && allow_new && core_ready;
 assign out_valid=run && !credit_fault && core_ov && (!ENABLE || rx_owned<CAPACITY);
 assign tx_valid=run && !credit_fault && core_tv;
 assign rx_ready=run && !credit_fault && core_rr;
 assign available=ENABLE ? credits:CAPACITY;
 assign rx_debt=ENABLE ? rx_owned:0;
 assign ack_pop=pop_total;
 assign fault=credit_fault || core_fault;
 ot_hbm_link_retry_sram #(.ENABLE(ENABLE),.W(W),.SW(SW),.EW(EW),.DEPTH(DEPTH),.TIMEOUT(TIMEOUT),.MAX_RETRY(MAX_RETRY),.NOEPOCH(NOEPOCH),.HEAD_FREE(PIPE_FIX),.SESREG(SESREG),.MUXREG(MUXREG)) u_retry(
 .clk(clk),.rst_n(run),.session(session),.in_valid(in_valid && allow_new && !credit_fault),.in_ready(core_ready),.in_data(in_data),
 .tx_valid(core_tv),.tx_ready(tx_ready && run && !credit_fault),.tx_data(tx_data),.tx_seq(tx_seq),.tx_session(tx_session),
 .rx_valid(rx_valid && run && !credit_fault),.rx_ready(core_rr),.rx_ue(rx_ue),.rx_data(rx_data),.rx_seq(rx_seq),.rx_session(rx_session),
 .out_valid(core_ov),.out_ready(consumer_ready && !credit_fault),.out_data(out_data),
 .ack_seq(ack_seq),.ack_nak(ack_nak),.ack_session(ack_session),
 .fb_valid(fb_valid),.fb_good(fb_good),.fb_nak(fb_nak),.fb_seq(fb_seq),.fb_session(fb_session),.fb_m(fb_m),
 .fault(core_fault),.retained(retained),.replay_count(replay_count));
 always @(posedge clk or negedge run) begin
  if(!run) begin credits<=CAPACITY;pop_seen<=0;pop_total<=0;rx_owned<=0;credit_fault<=0;end
  else if(ENABLE && !credit_fault) begin
`ifdef OT_HBM_TU_RETRY_MUT_FREE_CREDIT
   credits<=credits+(return_ok?pop_delta:0);
`else
   credits<=credits-(put?1'b1:1'b0)+(return_ok?pop_delta:0);
`endif
   if(return_ok)pop_seen<=fb_pop;
   if(pop_advance && !return_ok)credit_fault<=1;
   if(rx_consumed && rx_owned==0)credit_fault<=1;
   rx_owned<=rx_owned+(landed?1'b1:1'b0)-(consumed?1'b1:1'b0);
   if(consumed)pop_total<=pop_total+1'b1;
   if(landed && rx_owned>=CAPACITY && !consumed)credit_fault<=1;
  end
 end
 initial if(CAPACITY<2 || (CAPACITY&(CAPACITY-1)) || CAPACITY>=DEPTH) $fatal(1,"invalid conserved landing credit window");
endmodule
