// struct-close 2026-10-09 ("-cl" line; REVIEW_20261009 V17/X4, S4): UNGUARDED retry pipeline, same module name and ports
// as ot_hbm_link_retry_pipeline.sv (a route / bench uses ONE of the two files).  hbm-retry545-pipeline-pathfinding-r2
// (EPYC1TB) failed CTS at -1,427 ps on g_on.tx_parity -> fault (output port): the bookkeeping parity / poison checks
// (32-bit XOR trees over the 545-bit tx / rx registers, compared every cycle and ORed combinationally into fault,
// tx_valid and out_valid).  S4 REJECTED that protection everywhere (SECDED stays on the replay SRAM: rd_ue -> fault).
// Removed: tx/rx/mail/cap/delta/window parity, the inverted-classification copies and packet_poison; fault, tx_valid
// and out_valid now come from flops (fault_r) and the forward registers.  Retry / replay / ACK behaviour unchanged.
`timescale 1ns/1ps
// Structural closure candidate. Four-edge admission is real hardware pacing.
// Feedback mailbox coalesces cumulative ACKs; NAK is sticky until captured.
// Captured feedback advances through subtract, classify, then state update.
// No feedback combinational path reaches registered forward payload/valid.
// Coordinated reset must change session; old traffic cannot survive its wrap.
module ot_hbm_link_retry_pipeline #(
 parameter ENABLE=0,W=545,SW=12,EW=24,DEPTH=512,TIMEOUT=8192,MAX_RETRY=8,
 RSTR=`ifdef OT_RETRY_RSTR 1 `else 0 `endif,
 RX_SLOT_SAMPLE=`ifdef OT_RETRY_RX_SLOT_SAMPLE 1 `else 0 `endif,
 // [link] 2026-10-10 TX_SLOT_SAMPLE (opt-in): routed retry545 dp TT -69.75 / -85.73 = u_storage.seqp -> txd_u/D (22 levels):
 // the replay response tag compares (rd_seq vs read_target / cursor, rd_epoch vs session, generation, rewind) drove the
 // 545-bit txd_u load select in one edge.  The forward slot is the transmit twin of RX_SLOT_SAMPLE: txd_u samples its
 // source every edge the slot is EMPTY (!txv) and holds while occupied; the source is chosen by read_pending (a flop):
 // read_pending implies replaying, which closes in_ready, so the replay response and an admitted word are never both
 // possible.  All validation still gates txv (unchanged control block), so empty-slot contents are never visible.
 TX_SLOT_SAMPLE=`ifdef OT_RETRY_TX_SLOT_SAMPLE 1 `else 0 `endif,
 // [link] 2026-10-10 IN_PIN (opt-in): at the routed IO reference the remaining TT classes are INPUT PORT -> compare ->
 // flop (rx_session -> rxv / nak_pending / rxd_u, fb_session -> mail_seq: 14-17 levels after the 0.2 T + 150 ps budget).
 // Every rx_* / fb_* input lands in a pin register first (OT_WS_PINREG) and all validation runs on registered copies.
 //   rx: a raw pin slot rp (valid + tags + 545-bit payload, payload sampled while the slot is empty) feeds the visible
 //       landing slot.  A raw beat is judged only into an EMPTY landing slot (!rxv), so `expected` already counts every
 //       consumed item exactly as before; rx_ready = !rp_v.  Throughput is unchanged (one beat per 2 edges, as the
 //       landing bubble already imposed); +1 edge receive latency; +580 flops.
 //   fb: feedback inputs registered (+1 edge on ACK/NAK feedback; the mailbox coalescing is unchanged).
 IN_PIN=`ifdef OT_RETRY_IN_PIN 1 `else 0 `endif
)(
 input wire clk,rst_n,input wire [EW-1:0] session,
 input wire in_valid,output wire in_ready,input wire [W-1:0] in_data,
 output wire tx_valid,input wire tx_ready,output wire [W-1:0] tx_data,
 output wire [SW-1:0] tx_seq,output wire [EW-1:0] tx_session,
 input wire rx_valid,output wire rx_ready,input wire rx_ue,
 input wire [W-1:0] rx_data,input wire [SW-1:0] rx_seq,
 input wire [EW-1:0] rx_session,
 output wire out_valid,input wire out_ready,output wire [W-1:0] out_data,
 output wire [SW-1:0] ack_seq,output wire ack_nak,
 output wire [EW-1:0] ack_session,
 input wire fb_valid,fb_good,fb_nak,input wire [SW-1:0] fb_seq,
 input wire [EW-1:0] fb_session,
 output wire fault,output wire [SW-1:0] retained,output wire [31:0] replay_count
);
 // struct-close r4 (DRV6 re-judge: rst_n -> rxd recovery -652 / -668 on cl / cl2): RSTR = 1 = the SC-19 registered reset.
 // rst_n (pin) only feeds a 2-flop synchroniser (async assert, sync release; keep_hierarchy, beside the pin); every other
 // flop resets from rst_i, its registered output (+2 edges on the reset release, no change while running).
 wire rst_i;
 generate if (RSTR != 0) begin : g_rstr
 (* keep_hierarchy *) ot_retry_rst_sync u_rs (.clk(clk), .rst_n(rst_n), .rst_o(rst_i));
 end else begin : g_rdir
 assign rst_i = rst_n;
 end endgenerate
 // struct-close r5 (drive-0849: cl4 hm10 EF -433.5 = input session[18] -> g_on.txd (638 ps cell, fo 7), tx_session a
 // combinational pass-through, rst_i recovery -252 into the 1,090 txd / rxd flops): with RSTR the session is a pin
 // register (it only changes under the coordinated reset, which now releases 2 edges later), tx_session / ack_session
 // leave that register, and the wide payload registers txd / rxd are NOT reset (valid-qualified; loaded only by the
 // reset-released control state), so the reset net drives the control flops only.
 reg [EW-1:0] session_q;
 always @(posedge clk) session_q <= session;
 wire [EW-1:0] session_i = (RSTR != 0) ? session_q : session;
 generate if(!ENABLE) begin:g_off
 assign in_ready=tx_ready;assign tx_valid=in_valid;assign tx_data=in_data;
 assign tx_seq=0;assign tx_session=session_i;
 assign out_valid=rx_valid;assign rx_ready=out_ready;assign out_data=rx_data;
 assign ack_seq=0;assign ack_nak=0;assign ack_session=session_i;
 assign fault=0;assign retained=0;assign replay_count=0;
 end else begin:g_on
 reg [1:0] phase;
 reg [SW-1:0] base,next_seq,sent_seq,cursor,expected;
 reg [SW-1:0] debt_pipe;
 reg full_pipe;
 reg fault_r,replaying,nak_pending,nak_seen;
 reg [SW-1:0] last_nak;
 reg [31:0] retries;
 // struct-close r3: the replay counter leaves the fault_r-gated state block (fault_r -> retries[31:30] reg2reg -187 ps,
 // 36 endpoints: fault_r gated a 32-bit increment).  rinc is a one-cycle pulse set by the rewind; the counter adds it
 // one edge later in its own block (+1 cycle on the replay_count status only).
 reg rinc;
 always @(posedge clk or negedge rst_i) if(!rst_i) retries<=0; else if(rinc) retries<=retries+1'b1;
 localparam TW=$clog2(TIMEOUT+1),RW=$clog2(MAX_RETRY+2);
 reg [TW-1:0] timer;
 reg [RW-1:0] attempts;
 reg timeout_pending;
 reg txv,tx_replay;reg [W-1:0] txd;reg [SW-1:0] txs;
 reg rxv;reg [W-1:0] rxd;
 reg mail_v,mail_nak;reg [SW-1:0] mail_seq;
 reg cap_v,cap_nak;reg [SW-1:0] cap_seq,cap_base,cap_sent;
 reg [SW-1:0] delta_pipe,window_pipe;
 reg ack_progress,invalid_ack,fresh_nak;
 reg read_pending;reg [SW-1:0] read_target;
 reg read_generation,generation;
 reg [1:0] write_guard;
 wire rd_v,rd_ce,rd_ue;wire [W-1:0] rd_data;
 wire [SW-1:0] rd_seq;wire [EW-1:0] rd_epoch;
 // IN_PIN pin registers (pass-through when IN_PIN = 0)
 wire fbe_valid,fbe_good,fbe_nak;wire [SW-1:0] fbe_seq;wire [EW-1:0] fbe_session;
 reg rp_v;
 wire rj_v,rj_ue;wire [SW-1:0] rj_seq;wire [EW-1:0] rj_session;wire [W-1:0] rj_data;
 if (IN_PIN != 0) begin : g_inpin
  reg fq_valid,fq_good,fq_nak;reg [SW-1:0] fq_seq;reg [EW-1:0] fq_session;
  always @(posedge clk or negedge rst_i) if(!rst_i) fq_valid<=1'b0; else fq_valid<=fb_valid;
  always @(posedge clk) begin fq_good<=fb_good;fq_nak<=fb_nak;fq_seq<=fb_seq;fq_session<=fb_session; end
  assign fbe_valid=fq_valid;assign fbe_good=fq_good;assign fbe_nak=fq_nak;assign fbe_seq=fq_seq;assign fbe_session=fq_session;
  reg rq_ue;reg [SW-1:0] rq_seq;reg [EW-1:0] rq_session;reg [W-1:0] rq_data;
  // raw slot payload/tags: sampled every edge the raw slot is empty (enable = one flop), held while occupied
`ifndef OT_RETRY_MUT_IN_PIN_HOLD
  always @(posedge clk) if(!rp_v) begin rq_ue<=rx_ue;rq_seq<=rx_seq;rq_session<=rx_session;rq_data<=rx_data; end
`else
  always @(posedge clk) begin rq_ue<=rx_ue;rq_seq<=rx_seq;rq_session<=rx_session;rq_data<=rx_data; end   // mutant: raw slot not held
`endif
  assign rj_v=rp_v&&!rxv;assign rj_ue=rq_ue;assign rj_seq=rq_seq;assign rj_session=rq_session;assign rj_data=rq_data;
 end else begin : g_inpass
  assign fbe_valid=fb_valid;assign fbe_good=fb_good;assign fbe_nak=fb_nak;assign fbe_seq=fb_seq;assign fbe_session=fb_session;
  assign rj_v=rx_valid&&rx_ready;assign rj_ue=rx_ue;assign rj_seq=rx_seq;assign rj_session=rx_session;assign rj_data=rx_data;
 end
 wire [SW-1:0] rx_delta=rj_seq-expected;
 wire feedback=fbe_valid&&fbe_good&&fbe_session==session_i;
 wire apply=phase==3;
 wire rewind=apply&&(fresh_nak||timeout_pending);
 wire accepted=in_valid&&in_ready;
 wire launched=txv&&tx_ready&&!fault_r;
 wire request_read=phase==0&&replaying&&!read_pending&&!txv&&
   cursor!=sent_seq&&write_guard==0&&!fault_r;
 `ifndef OT_RETRY_MUT_RSTR_NOGATE
 assign in_ready=(RSTR==0||rst_i)&&phase==0&&!fault_r&&!replaying&&!txv&&!full_pipe;   // RSTR: no admission until the registered reset releases
`else
 assign in_ready=phase==0&&!fault_r&&!replaying&&!txv&&!full_pipe;   // mutant: admission while the core is still in reset
`endif
 // RSTR: unreset payload registers, loaded under exactly the conditions of the control block (else branch: !fault_r)
 wire txd_ld_rd = rd_v&&!rd_ue&&read_generation==generation&&rd_seq==read_target&&rd_seq==cursor&&rd_epoch==session_i&&!rewind;
 wire rxd_ld = rx_valid&&rx_ready&&rx_session==session_i&&!rx_ue&&rx_seq==expected;
 // Free-slot capture: validation still gates rxv. Empty-slot data is invisible;
 // once occupied, payload must remain stable until out_ready consumes it.
`ifndef OT_RETRY_MUT_RX_SLOT_HOLD
 wire rxd_payload_ld = (RX_SLOT_SAMPLE != 0) ? !rxv : rxd_ld;
`else
 wire rxd_payload_ld = (RX_SLOT_SAMPLE != 0) ? 1'b1 : rxd_ld;
`endif
 reg [W-1:0] txd_u, rxd_u;
 always @(posedge clk) if (rst_i && !fault_r) begin
`ifndef OT_RETRY_MUT_TX_SLOT_HOLD
  if (TX_SLOT_SAMPLE != 0) begin if (!txv) txd_u <= read_pending ? rd_data : in_data; end
`else
  if (TX_SLOT_SAMPLE != 0) txd_u <= read_pending ? rd_data : in_data;   // mutant: occupied slot not held
`endif
  else if (txd_ld_rd) txd_u <= rd_data; else if (accepted) txd_u <= in_data;
`ifndef OT_RETRY_MUT_RXD_U
  if (IN_PIN != 0) begin if (!rxv) rxd_u <= rj_data; end
  else if (rxd_payload_ld) rxd_u <= rx_data;
`else
  if (rxd_payload_ld && rx_seq[0]) rxd_u <= rx_data;   // mutant: odd-sequence payloads only (the shadow load condition broken)
`endif
 end
 assign tx_valid=txv&&!fault_r;assign tx_data=(RSTR!=0)?txd_u:txd;assign tx_seq=txs;
 assign tx_session=session_i;
 assign out_valid=rxv&&!fault_r;assign out_data=(RSTR!=0)?rxd_u:rxd;
 // Conservatively leave a bubble when the landing register is occupied.
 assign rx_ready=(RSTR==0||rst_i)&&(((IN_PIN!=0)?!rp_v:!rxv)||fault_r);
 assign ack_seq=expected;assign ack_nak=nak_pending;assign ack_session=session_i;
 // struct-close r2: retained (next_seq - base, a 12-bit subtract) was the -cl routes' only failing class: reg->out -513
 // (hbm_retry545_cl-958d0b4b1 x3).  Registered status: +1 cycle on the debt report, nothing else changes.
 reg [SW-1:0] retained_q;
 always @(posedge clk or negedge rst_i) if(!rst_i) retained_q<=0; else retained_q<=next_seq-base;
 assign retained=retained_q;assign fault=fault_r;assign replay_count=retries;
 ot_hbm_replay_sram #(.W(W),.SW(SW),.EW(EW),.DEPTH(DEPTH)) u_storage(
 .clk(clk),.rst_n(rst_i),.w_valid(accepted),.w_data(in_data),
 .w_seq(next_seq),.w_session(session_i),.r_valid(request_read),
 .r_seq(cursor),.r_session(session_i),.o_valid(rd_v),.o_data(rd_data),
 .o_seq(rd_seq),.o_session(rd_epoch),.o_ce(rd_ce),.o_ue(rd_ue));
 initial begin
 if(DEPTH<2||(DEPTH&(DEPTH-1))!=0||DEPTH>=(1<<(SW-1)))$fatal(1,"ambiguous replay window");
 if(TIMEOUT<8||MAX_RETRY<1)$fatal(1,"invalid retry bound");
 end
 always @(posedge clk or negedge rst_i) begin
 if(!rst_i) begin
 phase<=0;base<=0;next_seq<=0;sent_seq<=0;cursor<=0;expected<=0;
 debt_pipe<=0;full_pipe<=0;fault_r<=0;replaying<=0;nak_pending<=0;
 nak_seen<=0;last_nak<=0;rinc<=0;timer<=0;attempts<=0;
 timeout_pending<=0;txv<=0;tx_replay<=0;txd<=0;txs<=0;rxv<=0;rxd<=0;rp_v<=0;
 mail_v<=0;mail_nak<=0;mail_seq<=0;cap_v<=0;cap_nak<=0;cap_seq<=0;
 cap_base<=0;cap_sent<=0;delta_pipe<=0;window_pipe<=0;
 ack_progress<=0;invalid_ack<=0;fresh_nak<=0;
 read_pending<=0;read_target<=0;generation<=0;read_generation<=0;write_guard<=0;
 end else if(fault_r) rinc<=0;
 else begin
 rinc<=0;
 phase<=phase+1'b1;
 if(write_guard!=0)write_guard<=write_guard-1'b1;
 if(feedback)begin
 mail_v<=1;mail_seq<=fbe_seq;mail_nak<=mail_nak|fbe_nak;
 end
 if(phase==0)begin
 cap_v<=mail_v;cap_nak<=mail_nak;cap_seq<=mail_seq;
 cap_base<=base;cap_sent<=sent_seq;
 mail_v<=feedback;mail_nak<=feedback&&fbe_nak;
 end
 if(phase==1)begin
 delta_pipe<=cap_seq-cap_base;window_pipe<=cap_sent-cap_base;
 debt_pipe<=next_seq-base;
 end
 if(phase==2)begin
 ack_progress<=cap_v&&delta_pipe!=0&&delta_pipe<=window_pipe;
 invalid_ack<=cap_v&&!delta_pipe[SW-1]&&delta_pipe>window_pipe;
 fresh_nak<=cap_v&&cap_nak&&delta_pipe<=window_pipe&&
   (!nak_seen||cap_seq!=last_nak);
 full_pipe<=debt_pipe>=DEPTH;
 end
 if(accepted)begin
 txv<=1;tx_replay<=0;txd<=in_data;txs<=next_seq;
 
 next_seq<=next_seq+1'b1;write_guard<=2;
 end
 if(launched)begin
 txv<=0;
 if(tx_replay)begin
 cursor<=txs+1'b1;
 if(txs+1'b1==sent_seq)replaying<=0;
 end else sent_seq<=sent_seq+1'b1;
 end
 if(request_read)begin
 read_pending<=1;read_target<=cursor;read_generation<=generation;
 end
 if(rd_v)begin
 read_pending<=0;
 if(rd_ue)fault_r<=1;
 else if(read_generation==generation&&rd_seq==read_target&&
    rd_seq==cursor&&rd_epoch==session_i&&!rewind)begin
 txv<=1;tx_replay<=1;txd<=rd_data;txs<=rd_seq;
 
 end
 end
 if(next_seq==base)begin timer<=0;timeout_pending<=0;end
 else if(timer<TIMEOUT)timer<=timer+1'b1;
 else timeout_pending<=1;
 if(apply)begin
 begin
 if(invalid_ack)fault_r<=1;
 if(ack_progress)begin
 base<=cap_seq;timer<=0;timeout_pending<=0;attempts<=0;nak_seen<=0;
 end
 if(fresh_nak)begin nak_seen<=1;last_nak<=cap_seq;end
 if(rewind)begin
 cursor<=ack_progress?cap_seq:base;generation<=~generation;
 replaying<=1;timer<=0;timeout_pending<=0;rinc<=1;
 attempts<=ack_progress?1:attempts+1'b1;
 // A normal buffered packet remains retained and launches before replay.
 if(tx_replay)begin txv<=0;end
 if(!ack_progress&&attempts>=MAX_RETRY)fault_r<=1;
 end
 end
 end
 // Replays may resend ACKed data: receiver removes duplicates, preserving order.
 if(replaying&&!txv&&!read_pending&&cursor==sent_seq)replaying<=0;
 if(rxv&&out_ready)begin
 rxv<=0;
`ifndef OT_HBM_RETRY_PIPE_MUT_DUPLICATE
 expected<=expected+1'b1;
`endif
 nak_pending<=0;
 end
 if(IN_PIN!=0)begin
 if(rj_v)rp_v<=0;
 if(rx_valid&&rx_ready)rp_v<=1;
 end
 if(rj_v&&rj_session==session_i)begin
 if(!rj_ue&&rj_seq==expected)begin rxv<=1;rxd<=rj_data;end
 else if(rj_ue||!rx_delta[SW-1])nak_pending<=1;
 end
 end
 end
 end
 endgenerate
endmodule

// 2-flop reset synchroniser (async assert, sync release): the only load of the reset pin when RSTR = 1
module ot_retry_rst_sync (input wire clk, input wire rst_n, output wire rst_o);
 reg [1:0] r;
 always @(posedge clk or negedge rst_n) if (!rst_n) r <= 2'b00; else r <= {r[0], 1'b1};
 assign rst_o = r[1];
endmodule
