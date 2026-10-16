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
 parameter MUXREG=0,    // redesign-ds: replay SRAM registered bank select (ot_hbm_replay_sram MUXREG)
 parameter RREADY=0,    // hardcore-1010 B: registered-state in_ready (ot_hbm_link_retry_sram RREADY)
 // CPIPE (tu-retry-1010, 2026-10-10, default 0): pipelined source-credit counter with a conservative reservation.
 // turetryphy-fb-f63e6e650-a TT -33.9 = one 25-level cycle: credits -> tx_owned=CAP-credits -> pop_delta<=tx_owned ->
 // return_ok -> credits +/- (put, delta), with put = in_valid && in_ready (u_retry.replaying ... core_ready) inside it.
 // CPIPE=1 splits it:
 //  stage 1 (feedback edge, same edge as CPIPE=0): the over-return check no longer reads credits.  owned = put_cnt -
 //   pop_seen (mod 2^CW) is the exact flit count owed by the far end (invariant CAP-credits_orig == put_cnt-pop_seen:
 //   both move on the same put / accepted-return events), so pop_delta <= owned <=> !(put_cnt - fb_pop)[CW-1]
 //   (owned <= CAP = 2^(CW-2), 0 < delta < 2^(CW-1): the difference fits the signed CW-bit range).  pop_seen advances
 //   on an accepted return exactly as before; the accepted amount is registered (r_ret, r_ret-1) and a rejected one
 //   registers r_bad.
 //  stage 2 (next edge): credits <= put ? credits+r_ret-1 : credits+r_ret (both sums from flops, put is a final select);
 //   credit_fault <= r_bad.
 // Reservation proof: a put is charged on its own edge, a return is credited one edge late, so credits_pipe =
 // CAP - owned - r_ret <= CAP - owned: allow_new (credits != 0) implies owned < CAP before the put -- no over-issue,
 // ever (credits never exceeds the true free count).  credits_pipe >= 0 since owned + r_ret = owned before the return.
 // Cost: a returned credit becomes usable one pclk later; a forged / over-return faults one pclk later (no state from
 // it is applied: r_ret = 0 on a rejected return).  Fault-free delivered stream unchanged.
 parameter CPIPE=`ifdef OT_TU_CPIPE 1 `else 0 `endif
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
 wire pop_advance=fb_current && fb_pop!=pop_seen && !pop_delta[CW-1];
 // CPIPE: exact owed count from the put counter (no credits in the check); CPIPE=0: the original form
 reg[CW-1:0] put_cnt,r_ret,r_ret_m1;reg r_bad;
 wire[CW-1:0] own_less=put_cnt-fb_pop;
 wire[CW-1:0] tx_owned=CAPACITY-credits;
`ifdef OT_TU_CPIPE_RET_MUT
 wire return_ok=CPIPE ? pop_advance : (pop_advance && pop_delta<=tx_owned);   // negative control: no over-return check
`else
 wire return_ok=CPIPE ? (pop_advance && !own_less[CW-1]) : (pop_advance && pop_delta<=tx_owned);
`endif
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
 ot_hbm_link_retry_sram #(.ENABLE(ENABLE),.W(W),.SW(SW),.EW(EW),.DEPTH(DEPTH),.TIMEOUT(TIMEOUT),.MAX_RETRY(MAX_RETRY),.NOEPOCH(NOEPOCH),.HEAD_FREE(PIPE_FIX),.SESREG(SESREG),.MUXREG(MUXREG),.RREADY(RREADY)) u_retry(
 .clk(clk),.rst_n(run),.session(session),.in_valid(in_valid && allow_new && !credit_fault),.in_ready(core_ready),.in_data(in_data),
 .tx_valid(core_tv),.tx_ready(tx_ready && run && !credit_fault),.tx_data(tx_data),.tx_seq(tx_seq),.tx_session(tx_session),
 .rx_valid(rx_valid && run && !credit_fault),.rx_ready(core_rr),.rx_ue(rx_ue),.rx_data(rx_data),.rx_seq(rx_seq),.rx_session(rx_session),
 .out_valid(core_ov),.out_ready(consumer_ready && !credit_fault),.out_data(out_data),
 .ack_seq(ack_seq),.ack_nak(ack_nak),.ack_session(ack_session),
 .fb_valid(fb_valid),.fb_good(fb_good),.fb_nak(fb_nak),.fb_seq(fb_seq),.fb_session(fb_session),.fb_m(fb_m),
 .fault(core_fault),.retained(retained),.replay_count(replay_count));
 if(CPIPE)begin:g_cpipe
`ifdef OT_TU_CPIPE_OVR_MUT
  // negative control (credit overrun): the naive pipelining -- the put is charged one edge LATE (put_q), so allow_new
  // still sees the pre-put count and the 257th flit is accepted against a 256-flit landing window
  reg put_q;always@(posedge clk or negedge run)if(!run)put_q<=0;else put_q<=ENABLE && !credit_fault && put;
  wire chg=put_q;
`else
  wire chg=put;
`endif
  wire[CW-1:0] c_np=credits+r_ret,c_p=credits+r_ret_m1;
  always @(posedge clk or negedge run) begin
   if(!run) begin credits<=CAPACITY;put_cnt<=0;r_ret<=0;r_ret_m1<={CW{1'b1}};r_bad<=0;end
   else if(ENABLE && !credit_fault) begin
    credits<=chg ? c_p:c_np;
    if(put)put_cnt<=put_cnt+1'b1;
    r_ret<=return_ok ? pop_delta:{CW{1'b0}};
    r_ret_m1<=return_ok ? pop_delta-1'b1:{CW{1'b1}};
    r_bad<=pop_advance && !return_ok;
   end
  end
`ifndef SYNTHESIS
  // reservation invariant (simulation): credits + in-flight return == CAP - owed, and owed never exceeds CAP
  wire[CW-1:0] owed=put_cnt-pop_seen;   // CW-bit modular difference (owed <= CAP < 2^(CW-1))
  always @(posedge clk) if(ENABLE && run && !credit_fault && !r_bad) begin
   if(owed>CAPACITY) $display("FATAL: CPIPE owed %0d > CAPACITY",owed);
   if(credits+r_ret+owed!=CAPACITY) $display("FATAL: CPIPE reservation credits %0d + in-flight %0d + owed %0d != CAPACITY",credits,r_ret,owed);
  end
`endif
 end else begin:g_cdir
  always @(posedge clk or negedge run) begin
   if(!run) credits<=CAPACITY;
   else if(ENABLE && !credit_fault)
`ifdef OT_HBM_TU_RETRY_MUT_FREE_CREDIT
    credits<=credits+(return_ok?pop_delta:0);
`else
    credits<=credits-(put?1'b1:1'b0)+(return_ok?pop_delta:0);
`endif
  end
  always @(posedge clk) begin put_cnt<=0;r_ret<=0;r_ret_m1<=0;r_bad<=0;end
 end
 always @(posedge clk or negedge run) begin
  if(!run) begin pop_seen<=0;pop_total<=0;rx_owned<=0;credit_fault<=0;end
  else if(ENABLE && !credit_fault) begin
   if(return_ok)pop_seen<=fb_pop;
   if(CPIPE ? r_bad : (pop_advance && !return_ok))credit_fault<=1;
   if(rx_consumed && rx_owned==0)credit_fault<=1;
   rx_owned<=rx_owned+(landed?1'b1:1'b0)-(consumed?1'b1:1'b0);
   if(consumed)pop_total<=pop_total+1'b1;
   if(landed && rx_owned>=CAPACITY && !consumed)credit_fault<=1;
  end
 end
 initial if(CAPACITY<2 || (CAPACITY&(CAPACITY-1)) || CAPACITY>=DEPTH) $fatal(1,"invalid conserved landing credit window");
endmodule
