`timescale 1ns/1ps
// Default-off RQ-HS7 protocol endpoint, one clock. FEC UE causes go-back-N.
// tx_ready must include conserved receiver landing credits; not a wire ready.
// Session must change on coordinated reset/train and not wrap with old traffic.
// Real SECDED SRAM successor. Read reservation/scheduler exists in this module.
// Receiver landing credit bridge and physical SS/FF remain integration gates.
module ot_hbm_link_retry_sram #(
 parameter ENABLE=0, W=551, SW=12, EW=16, DEPTH=512,
 parameter TIMEOUT=2048, MAX_RETRY=8,
 // NOEPOCH=1 (sys-takeover 2026-10-09, opt-in; review S4/S5): no session/epoch identity and no sequence in the stored
 // record or its checks; SECDED covers the replay payload only.  Go-back-N sequence numbers on the link are unchanged.
 parameter NOEPOCH=0,
 // HEAD_FREE (cont-takeover 2026-10-09, default 0): replay_head / head_seq load on every read response (no reset);
 // head_valid alone carries the acceptance condition.  A read is requested only with head_valid low, so the overwrite
 // never replaces a valid head.  Removes the 551-bit enable from the feedback -> rewind cone (TU -lkv pclk -499).
 parameter HEAD_FREE=0,
 // SESREG (redesign-ds 2026-10-09, default 0; keeps every session check, NOEPOCH=0): (1) the feedback session match
 // arrives as a registered 1-bit fb_m (computed by the caller one edge earlier) instead of a live 24-bit fb_session ==
 // session compare in the feedback -> rewind -> tx_valid -> send cone (TU iqs2-a -452); (2) the replay read's stored-
 // epoch check reads a per-slot flag (set when the slot is written, all cleared when the session changes) captured at
 // the read request, instead of read_epoch == session.  Equal to the compares under this module's own contract:
 // "session must change on coordinated reset/train and not wrap with old traffic".
 parameter SESREG=0,
 parameter MUXREG=0,     // redesign-ds: ot_hbm_replay_sram MUXREG (+1 read edge; reads are reserved / latency insensitive)
 // RREADY (hardcore-1010 grp B fallback, default 0): in_ready is a function of REGISTERED state only (fault, replaying,
 // debt, tx_ready); the same-cycle feedback classification (advance / debt compares -> rewind) no longer gates it, and
 // the fresh-send term of tx_valid no longer waits out a rewind cycle.  A flit accepted in the rewind cycle is launched
 // and written at next_seq as usual; the go-back-N replay that the rewind starts covers [cursor, next_seq) and resends
 // it (write_guard holds the replay read until the write lands); the receiver drops the out-of-order / duplicate copy
 // exactly as for any in-flight flit after a NAK.  Fault-free streams are cycle-identical (rewind never fires).
 parameter RREADY=0,
 // FBPRE (tu-retry-1011, default 0; needs SESREG, whose feedback register makes fb_seq_nx = next cycle's fb_seq):
 // cp-9e7cf26ca-b post-CTS TT -79..-30 = base -> advance/debt subtracts + compare -> ack_progress / rewind /
 // replay_empty -> {tx_valid -> u_tx, credits, fault, attempts, cursor}, and base -> debt<DEPTH -> in_ready -> accepted
 // -> every accept-enabled register.  The base-dependent compares are evaluated one cycle EARLY from registers: for each
 // of the four possible next states (base or fb_seq) x (next_seq or next_seq+1) the exact original expressions
 // (advance<=debt, advance!=0, advance[MSB], fb_seq==next_seq, debt<DEPTH, debt!=0) are formed against fb_seq_nx, and
 // the edge picks the one the state registers actually take (ack_progress / accepted are the final 2:1 selects).
 // Cycle-exact: every flag equals the live expression in every cycle (OT_TU_FBPRE_CHECK asserts it).
 parameter FBPRE=0,
 // SFPIPE (tu-retry-1011, default 0, SESREG only): the per-slot session flag set is applied one edge after the accept
 // (cp-9e7cf26ca-b -50: fault -> in_ready -> accepted -> 512 sflag enables).  A set accepted in a session-change cycle
 // is dropped as before; the flag is read only by a replay read, which write_guard (2 edges) keeps >= 3 edges after
 // the accept, so every rflag read is unchanged (OT_TU_SESREG_CHECK compares it with the stored epoch on every read).
 parameter SFPIPE=0
)(
 input wire clk, rst_n, input wire [EW-1:0] session,
 input wire in_valid, output wire in_ready, input wire [W-1:0] in_data,
 output wire tx_valid, input wire tx_ready,
 output wire [W-1:0] tx_data, output wire [SW-1:0] tx_seq,
 output wire [EW-1:0] tx_session,
 input wire rx_valid, output wire rx_ready, input wire rx_ue,
 input wire [W-1:0] rx_data, input wire [SW-1:0] rx_seq,
 input wire [EW-1:0] rx_session,
 output wire out_valid, input wire out_ready, output wire [W-1:0] out_data,
 output wire [SW-1:0] ack_seq, output wire ack_nak,
 output wire [EW-1:0] ack_session,
 input wire fb_valid, fb_good, fb_nak,
 input wire [SW-1:0] fb_seq, input wire [EW-1:0] fb_session,
 input wire fb_m,
 input wire [SW-1:0] fb_seq_nx,   // FBPRE: the value fb_seq takes at the next edge (unconnected otherwise)
 output reg fault, output wire [SW-1:0] retained,
 output reg [31:0] replay_count
);
 localparam AW=$clog2(DEPTH);
 reg [W-1:0] replay_head;
 reg head_valid, read_pending;
 reg [SW-1:0] head_seq;
 reg [1:0] write_guard;
 wire read_response, read_ce, read_ue;
 wire [W-1:0] read_data;
 wire [SW-1:0] read_seq;
 wire [EW-1:0] read_epoch;
 wire request_read=ENABLE && replaying && !read_pending && !head_valid &&
                   write_guard==0 && !rewind && !fault && !replay_empty;
 ot_hbm_replay_sram #(.W(W),.SW(SW),.EW(EW),.DEPTH(DEPTH),.NOEPOCH(NOEPOCH),.MUXREG(MUXREG)) u_storage(
  .clk(clk),.rst_n(rst_n),.w_valid(ENABLE && accepted),.w_data(in_data),
  .w_seq(next_seq),.w_session(session),.r_valid(request_read),
  .r_seq(replay_seq),.r_session(session),.o_valid(read_response),
  .o_data(read_data),.o_seq(read_seq),.o_session(read_epoch),.o_ce(read_ce),.o_ue(read_ue));

 reg [SW-1:0] base, next_seq, cursor, expected;
 reg replaying, nak_pending, nak_seen;
 reg [SW-1:0] last_nak;
 integer timer, attempts;
 wire [SW-1:0] debt=next_seq-base;
 wire [SW-1:0] advance=fb_seq-base;
 wire feedback=fb_valid && fb_good && (NOEPOCH || (SESREG ? fb_m : fb_session==session));
 // FBPRE: registered flags (see the parameter); the live expressions otherwise
 reg p_le,p_nz,p_st,p_eq,p_room,p_dnz;
 wire f_le=FBPRE ? p_le : advance<=debt;
 wire f_nz=FBPRE ? p_nz : advance!=0;
 wire f_st=FBPRE ? p_st : advance[SW-1];
 wire f_eq=FBPRE ? p_eq : fb_seq==next_seq;
 wire f_room=FBPRE ? p_room : debt<DEPTH;
 wire f_dnz=FBPRE ? p_dnz : debt!=0;
 wire ack_progress=feedback && f_nz && f_le;
 wire stale=f_st;
 wire invalid_ack=feedback && !f_le && !stale;
 wire timeout_hit=f_dnz && timer>=TIMEOUT-1;
 wire fresh_nak=feedback && fb_nak && f_le && (!nak_seen || fb_seq!=last_nak);
 wire rewind=fresh_nak || timeout_hit;
 wire [SW-1:0] cursor_delta=fb_seq-cursor;
 wire [SW-1:0] replay_seq=cursor;
 wire replay_empty=ack_progress && f_eq;
 assign retained=ENABLE ? debt:0;
`ifdef OT_TU_RREADY_MUT
 wire rr_mut=1'b1;   // negative control: new flits are accepted during a replay (order must break)
`else
 wire rr_mut=1'b0;
`endif
 assign in_ready=!ENABLE ? tx_ready:(RREADY ? (!fault && (!replaying || rr_mut) && f_room && tx_ready)
                                            : (!fault && !replaying && !rewind && f_room && tx_ready));
 assign tx_valid=!ENABLE ? in_valid:!fault && ((!rewind && replaying && head_valid && head_seq==cursor && !replay_empty) ||
                                            ((!replaying || (RREADY && rr_mut)) && in_valid && f_room && (RREADY || !rewind)));
 assign tx_data=ENABLE && replaying && !(RREADY && rr_mut) ? replay_head:in_data;
 assign tx_seq=ENABLE ? (replaying ? replay_seq:next_seq):0;
 assign tx_session=session;
 wire accepted=in_valid && in_ready;
 wire launched=tx_valid && tx_ready;
 if(FBPRE)begin:g_fbpre
  // next-state candidates: b in {base, fb_seq} (ack_progress moves base to fb_seq), n in {next_seq, next_seq+1}
  wire[SW-1:0] x=fb_seq_nx, n1=next_seq+1'b1;
  wire[SW-1:0] a0=x-base, a1=x-fb_seq;
  wire[SW-1:0] d00=next_seq-base, d01=n1-base, d10=next_seq-fb_seq, d11=n1-fb_seq;
`ifdef OT_TU_FBPRE_UPD_MUT
  wire upd=1'b0;                                   // negative control: an ACK's base step is ignored
`else
  wire upd=ENABLE && !fault && ack_progress;      // base <= fb_seq at this edge
`endif
`ifdef OT_TU_FBPRE_MUT
  wire inc=1'b0;                                   // negative control: the accept's next_seq step is ignored
`else
  wire inc=ENABLE && !fault && accepted;           // next_seq <= next_seq+1 at this edge
`endif
  always @(posedge clk or negedge rst_n)
   if(!rst_n) begin p_le<=1'b1;p_nz<=1'b0;p_st<=1'b0;p_eq<=1'b1;p_room<=1'b1;p_dnz<=1'b0; end   // base = next_seq = 0
   else begin
    p_nz<=upd ? x!=fb_seq : x!=base;
    p_st<=upd ? a1[SW-1] : a0[SW-1];
    p_eq<=inc ? x==n1 : x==next_seq;
    case({upd,inc})
     2'b00: begin p_le<=a0<=d00; p_room<=d00<DEPTH; p_dnz<=d00!=0; end
     2'b01: begin p_le<=a0<=d01; p_room<=d01<DEPTH; p_dnz<=d01!=0; end
     2'b10: begin p_le<=a1<=d10; p_room<=d10<DEPTH; p_dnz<=d10!=0; end
     default: begin p_le<=a1<=d11; p_room<=d11<DEPTH; p_dnz<=d11!=0; end
    endcase
   end
`ifdef OT_TU_FBPRE_CHECK
  // bench-only exactness check: every registered flag equals the live expression in every enabled cycle
  always @(posedge clk) if(ENABLE && rst_n && !fault) begin
   if(p_room!==(debt<DEPTH) || p_dnz!==(debt!=0)) $fatal(1,"FBPRE window flag differs (debt %0d)",debt);
   if(fb_valid && (p_le!==(advance<=debt) || p_nz!==(advance!=0) || p_st!==advance[SW-1] || p_eq!==(fb_seq==next_seq)))
    $fatal(1,"FBPRE feedback flag differs (fb_seq %0d base %0d next %0d)",fb_seq,base,next_seq);
  end
  integer fbpre_n=0; always @(posedge clk) if(ENABLE && rst_n && !fault && feedback) fbpre_n=fbpre_n+1;
  final $display("FBPRE_CHECKED %0d feedback cycles",fbpre_n);
`endif
 end else begin:g_fbdir
  always @(posedge clk) begin p_le<=1'b0;p_nz<=1'b0;p_st<=1'b0;p_eq<=1'b0;p_room<=1'b0;p_dnz<=1'b0; end
 end
 wire current=NOEPOCH || rx_session==session;
 wire ordered=rx_seq==expected;
 wire [SW-1:0] rx_delta=rx_seq-expected;
 assign out_valid=!ENABLE ? rx_valid:rx_valid && current && !rx_ue && ordered && !fault;
 assign out_data=rx_data;
 assign rx_ready=!ENABLE ? out_ready:(!current || rx_ue || !ordered || fault) ? 1'b1:out_ready;
 assign ack_seq=expected;
 assign ack_nak=nak_pending;
 assign ack_session=session;
 // SESREG: per-slot "written in the current session" flags
 reg [DEPTH-1:0] sflag; reg [EW-1:0] ses_prev; reg rflag;
 reg sf_v; reg [AW-1:0] sf_i;   // SFPIPE: the accepted slot, set one edge later
`ifdef OT_TU_SFPIPE_MUT
 wire sf_go=1'b0;                   // negative control: the delayed set never lands (replays must then stall)
`else
 wire sf_go=sf_v;
`endif
 wire [AW-1:0] sf_slot=sf_i;
 wire sf_set=SFPIPE ? sf_go : accepted;
 wire [AW-1:0] sf_at=SFPIPE ? sf_slot : next_seq[AW-1:0];
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin sflag<=0; ses_prev<=0; rflag<=1'b0; sf_v<=1'b0; sf_i<=0; end
  else if(SESREG) begin
   ses_prev<=session;
   sf_v<=SFPIPE && accepted && session==ses_prev;
   sf_i<=next_seq[AW-1:0];
`ifdef OT_TU_SESREG_MUT_SLOT
   if(sf_set) sflag[sf_at]<=1'b1;                       // mutant: flags never cleared on a session change
`else
   if(session!=ses_prev) sflag<=0;
   else if(sf_set) sflag[sf_at]<=1'b1;
`endif
   if(request_read) rflag<=sflag[replay_seq[AW-1:0]];
  end
 wire epoch_ok=NOEPOCH || (SESREG ? rflag : read_epoch==session);
`ifdef OT_TU_FB_COVER
 // bench-only coverage: RREADY's new case (a fresh flit accepted and launched in a rewind cycle)
 integer rr_cov=0; always @(posedge clk) if(RREADY && ENABLE && rst_n && accepted && rewind) begin rr_cov=rr_cov+1;
  $display("RREADY_COVER accept-in-rewind #%0d seq %0d", rr_cov, next_seq); end
`endif
`ifdef OT_TU_SESREG_CHECK
 // bench-only equivalence check: the registered per-slot flag equals the live stored-epoch compare on every replay read
 always @(posedge clk) if(SESREG && ENABLE && rst_n && read_response && !read_ue && rflag!==(read_epoch==session))
  $fatal(1,"SESREG slot flag differs from the stored-epoch compare (seq %0d)", read_seq);
`endif
 initial begin
  if((FBPRE || SFPIPE) && !SESREG) $fatal(1,"FBPRE/SFPIPE need SESREG");
  if(DEPTH<2 || (DEPTH & (DEPTH-1))!=0 || DEPTH>=(1<<(SW-1))) $fatal(1,"ambiguous replay window");
  if(TIMEOUT<1 || MAX_RETRY<1) $fatal(1,"invalid retry bound");
 end
 always @(posedge clk) if(HEAD_FREE && ENABLE && read_response) begin replay_head<=read_data;head_seq<=read_seq; end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   base<=0; next_seq<=0; cursor<=0; expected<=0;
   head_valid<=0; read_pending<=0; write_guard<=0;
   replaying<=0; nak_pending<=0; nak_seen<=0; last_nak<=0; fault<=0; replay_count<=0; timer<=0; attempts<=0;
  end else if(ENABLE && !fault) begin
   if(invalid_ack) fault<=1;
   if(write_guard!=0) write_guard<=write_guard-1'b1;
   if(request_read) read_pending<=1;
   if(read_response) begin
    read_pending<=0;
    if(read_ue) fault<=1;
    else if(read_seq==cursor && epoch_ok && !rewind) begin
     if(!HEAD_FREE) begin replay_head<=read_data;head_seq<=read_seq; end
     head_valid<=1;
    end
   end
   if(launched && replaying) head_valid<=0;
   if(rewind || replay_empty) head_valid<=0;

   if(!f_dnz || ack_progress) begin timer<=0; attempts<=0; end
   else timer<=timer+1;
   if(ack_progress) begin
    base<=fb_seq; nak_seen<=0;
    if(replaying && !cursor_delta[SW-1]) begin cursor<=fb_seq;head_valid<=0;end
   end
   if(fresh_nak) begin nak_seen<=1; last_nak<=fb_seq; end
   if(accepted) begin
    write_guard<=2;
    next_seq<=next_seq+1'b1;
   end
   if(launched && replaying) begin
    cursor<=replay_seq+1'b1;
    if(replay_seq+1'b1==next_seq) replaying<=0;
   end
   if(replaying && ack_progress && fb_seq==next_seq) replaying<=0;
   if(rewind && (!ack_progress || fb_seq!=next_seq)) begin
    cursor<=ack_progress ? fb_seq:base;
    replaying<=1; timer<=0; replay_count<=replay_count+1;
    attempts<=ack_progress ? 1:attempts+1;
    if(!ack_progress && attempts>=MAX_RETRY) fault<=1;
   end
   if(rx_valid && rx_ready && current) begin
    if(!rx_ue && ordered) begin
`ifndef OT_HBM_RETRY_MUT_DUPLICATE
     expected<=expected+1'b1;
`endif
     nak_pending<=0;
    end else if(rx_ue || (!ordered && !rx_delta[SW-1])) nak_pending<=1;
   end
  end
 end
endmodule
