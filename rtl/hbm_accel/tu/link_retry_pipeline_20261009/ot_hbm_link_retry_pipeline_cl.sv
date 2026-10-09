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
 parameter ENABLE=0,W=545,SW=12,EW=24,DEPTH=512,TIMEOUT=8192,MAX_RETRY=8
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
 generate if(!ENABLE) begin:g_off
 assign in_ready=tx_ready;assign tx_valid=in_valid;assign tx_data=in_data;
 assign tx_seq=0;assign tx_session=session;
 assign out_valid=rx_valid;assign rx_ready=out_ready;assign out_data=rx_data;
 assign ack_seq=0;assign ack_nak=0;assign ack_session=session;
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
 always @(posedge clk or negedge rst_n) if(!rst_n) retries<=0; else if(rinc) retries<=retries+1'b1;
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
 wire [SW-1:0] rx_delta=rx_seq-expected;
 wire feedback=fb_valid&&fb_good&&fb_session==session;
 wire apply=phase==3;
 wire rewind=apply&&(fresh_nak||timeout_pending);
 wire accepted=in_valid&&in_ready;
 wire launched=txv&&tx_ready&&!fault_r;
 wire request_read=phase==0&&replaying&&!read_pending&&!txv&&
   cursor!=sent_seq&&write_guard==0&&!fault_r;
 assign in_ready=phase==0&&!fault_r&&!replaying&&!txv&&!full_pipe;
 assign tx_valid=txv&&!fault_r;assign tx_data=txd;assign tx_seq=txs;
 assign tx_session=session;
 assign out_valid=rxv&&!fault_r;assign out_data=rxd;
 // Conservatively leave a bubble when the landing register is occupied.
 assign rx_ready=!rxv||fault_r;
 assign ack_seq=expected;assign ack_nak=nak_pending;assign ack_session=session;
 // struct-close r2: retained (next_seq - base, a 12-bit subtract) was the -cl routes' only failing class: reg->out -513
 // (hbm_retry545_cl-958d0b4b1 x3).  Registered status: +1 cycle on the debt report, nothing else changes.
 reg [SW-1:0] retained_q;
 always @(posedge clk or negedge rst_n) if(!rst_n) retained_q<=0; else retained_q<=next_seq-base;
 assign retained=retained_q;assign fault=fault_r;assign replay_count=retries;
 ot_hbm_replay_sram #(.W(W),.SW(SW),.EW(EW),.DEPTH(DEPTH)) u_storage(
 .clk(clk),.rst_n(rst_n),.w_valid(accepted),.w_data(in_data),
 .w_seq(next_seq),.w_session(session),.r_valid(request_read),
 .r_seq(cursor),.r_session(session),.o_valid(rd_v),.o_data(rd_data),
 .o_seq(rd_seq),.o_session(rd_epoch),.o_ce(rd_ce),.o_ue(rd_ue));
 initial begin
 if(DEPTH<2||(DEPTH&(DEPTH-1))!=0||DEPTH>=(1<<(SW-1)))$fatal(1,"ambiguous replay window");
 if(TIMEOUT<8||MAX_RETRY<1)$fatal(1,"invalid retry bound");
 end
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin
 phase<=0;base<=0;next_seq<=0;sent_seq<=0;cursor<=0;expected<=0;
 debt_pipe<=0;full_pipe<=0;fault_r<=0;replaying<=0;nak_pending<=0;
 nak_seen<=0;last_nak<=0;rinc<=0;timer<=0;attempts<=0;
 timeout_pending<=0;txv<=0;tx_replay<=0;txd<=0;txs<=0;rxv<=0;rxd<=0;
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
 mail_v<=1;mail_seq<=fb_seq;mail_nak<=mail_nak|fb_nak;
 end
 if(phase==0)begin
 cap_v<=mail_v;cap_nak<=mail_nak;cap_seq<=mail_seq;
 cap_base<=base;cap_sent<=sent_seq;
 mail_v<=feedback;mail_nak<=feedback&&fb_nak;
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
    rd_seq==cursor&&rd_epoch==session&&!rewind)begin
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
 if(rx_valid&&rx_ready&&rx_session==session)begin
 if(!rx_ue&&rx_seq==expected)begin rxv<=1;rxd<=rx_data;end
 else if(rx_ue||!rx_delta[SW-1])nak_pending<=1;
 end
 end
 end
 end
 endgenerate
endmodule
