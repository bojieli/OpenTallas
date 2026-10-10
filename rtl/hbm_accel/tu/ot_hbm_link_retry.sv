`timescale 1ns/1ps
// Default-off RQ-HS7 protocol endpoint, one clock. FEC UE causes go-back-N.
// tx_ready must include conserved receiver landing credits; not a wire ready.
// Session must change on coordinated reset/train and not wrap with old traffic.
// Replay array is functional RTL. Protected SRAM/read pipeline integration OPEN.
module ot_hbm_link_retry #(
 parameter ENABLE=0, W=551, SW=12, EW=16, DEPTH=512,
 parameter TIMEOUT=2048, MAX_RETRY=8
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
 output reg fault, output wire [SW-1:0] retained,
 output reg [31:0] replay_count
);
 localparam AW=$clog2(DEPTH);
 reg [W-1:0] replay_mem[0:DEPTH-1];
 reg [SW-1:0] base, next_seq, cursor, expected;
 reg replaying, nak_pending, nak_seen;
 reg [SW-1:0] last_nak;
 integer timer, attempts;
 wire [SW-1:0] debt=next_seq-base;
 wire [SW-1:0] advance=fb_seq-base;
 wire feedback=fb_valid && fb_good && fb_session==session;
 wire ack_progress=feedback && advance!=0 && advance<=debt;
 wire stale=advance[SW-1];
 wire invalid_ack=feedback && advance>debt && !stale;
 wire timeout_hit=debt!=0 && timer>=TIMEOUT-1;
 wire fresh_nak=feedback && fb_nak && advance<=debt && (!nak_seen || fb_seq!=last_nak);
 wire rewind=fresh_nak || timeout_hit;
 wire [SW-1:0] cursor_delta=fb_seq-cursor;
 wire [SW-1:0] replay_seq=ack_progress && !cursor_delta[SW-1] ? fb_seq:cursor;
 wire replay_empty=ack_progress && fb_seq==next_seq;
 assign retained=ENABLE ? debt:0;
 assign in_ready=!ENABLE ? tx_ready:!fault && !replaying && !rewind && debt<DEPTH && tx_ready;
 assign tx_valid=!ENABLE ? in_valid:!fault && !rewind && ((replaying && !replay_empty) || (!replaying && in_valid && debt<DEPTH));
 assign tx_data=ENABLE && replaying ? replay_mem[replay_seq[AW-1:0]]:in_data;
 assign tx_seq=ENABLE ? (replaying ? replay_seq:next_seq):0;
 assign tx_session=session;
 wire accepted=in_valid && in_ready;
 wire launched=tx_valid && tx_ready;
 wire current=rx_session==session;
 wire ordered=rx_seq==expected;
 wire [SW-1:0] rx_delta=rx_seq-expected;
 assign out_valid=!ENABLE ? rx_valid:rx_valid && current && !rx_ue && ordered && !fault;
 assign out_data=rx_data;
 assign rx_ready=!ENABLE ? out_ready:(!current || rx_ue || !ordered || fault) ? 1'b1:out_ready;
 assign ack_seq=expected;
 assign ack_nak=nak_pending;
 assign ack_session=session;
 initial begin
  if(DEPTH<2 || (DEPTH & (DEPTH-1))!=0 || DEPTH>=(1<<(SW-1))) $fatal(1,"ambiguous replay window");
  if(TIMEOUT<1 || MAX_RETRY<1) $fatal(1,"invalid retry bound");
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   base<=0; next_seq<=0; cursor<=0; expected<=0;
   replaying<=0; nak_pending<=0; nak_seen<=0; last_nak<=0; fault<=0; replay_count<=0; timer<=0; attempts<=0;
  end else if(ENABLE && !fault) begin
   if(invalid_ack) fault<=1;
   if(debt==0 || ack_progress) begin timer<=0; attempts<=0; end
   else timer<=timer+1;
   if(ack_progress) begin base<=fb_seq; nak_seen<=0; end
   if(fresh_nak) begin nak_seen<=1; last_nak<=fb_seq; end
   if(accepted) begin
    replay_mem[next_seq[AW-1:0]]<=in_data;
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
