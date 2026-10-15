// Default-off lifetime candidate. Events are accepted handshakes, never paused
// core levels. A seal is an explicit whole-consumer drain certificate; local
// core_idle and cache response_capture are deliberately not connected here.
module ot_qwen_xdelivery_ack_bank #(
  parameter integer ENABLE=0, N=48, SEQ_W=40, COUNT_W=7,
  parameter integer ID_W=(N<2?1:$clog2(N))
)(
  input wire clk, rst_n,
  input wire begin_v, input wire [15:0] begin_context,
  input wire [31:0] begin_version,
  input wire [N-1:0] participant_mask,
  input wire issue_v, output wire issue_ready,
  input wire [ID_W-1:0] issue_id,
  input wire [SEQ_W-1:0] issue_seq,
  input wire [15:0] issue_context, input wire [31:0] issue_version,
  input wire retire_v, output wire retire_ready,
  input wire [ID_W-1:0] retire_id,
  input wire [SEQ_W-1:0] retire_seq,
  input wire [15:0] retire_context, input wire [31:0] retire_version,
  input wire seal_v, input wire [ID_W-1:0] seal_id,
  input wire [15:0] seal_context, input wire [31:0] seal_version,
  // Clear only after the external transport/replay reset fence is acknowledged.
  input wire fenced_clear,
  output wire drained, output reg fault
);
  reg active;
  reg [15:0] context_q;
  reg [31:0] version_q;
  reg [N-1:0] participants, sealed;
  reg [COUNT_W-1:0] outstanding [0:N-1];
  reg [SEQ_W-1:0] issued [0:N-1], retired [0:N-1];
  reg empty;
  integer i;
  wire issue_match=ENABLE && active && issue_id<N &&
    issue_context==context_q && issue_version==version_q;
  wire retire_match=ENABLE && active && retire_id<N &&
    retire_context==context_q && retire_version==version_q;
  // Sequence exhaustion requires a new fenced operation; no silent wrap.
  assign issue_ready=issue_match && !fault && participants[issue_id] &&
    !sealed[issue_id] && outstanding[issue_id]!={COUNT_W{1'b1}} &&
    issued[issue_id]!={SEQ_W{1'b1}} && issue_seq==issued[issue_id];
  assign retire_ready=retire_match && !fault && participants[retire_id] &&
    outstanding[retire_id]!=0 && retire_seq==retired[retire_id];
  always @* begin
    empty=1'b1;
    for(integer j=0;j<N;j=j+1)
      if(participants[j] && (!sealed[j] || outstanding[j]!=0)) empty=1'b0;
  end
  assign drained=ENABLE && active && empty && !fault;
  always @(posedge clk) begin
    if(!rst_n || fenced_clear) begin
      active<=0; context_q<=0; version_q<=0;
      participants<=0; sealed<=0; fault<=0;
      for(i=0;i<N;i=i+1) begin outstanding[i]<=0; issued[i]<=0; retired[i]<=0; end
    end else if(ENABLE) begin
      if(begin_v) begin
        if(issue_v || retire_v || seal_v) fault<=1; // BEGIN_EVENT_FENCE_SCALAR
        else if(active && !drained) fault<=1;
        else begin
          active<=1; context_q<=begin_context; version_q<=begin_version;
          participants<=participant_mask; sealed<=0;
          for(i=0;i<N;i=i+1) begin outstanding[i]<=0; issued[i]<=0; retired[i]<=0; end
        end
      end else begin
        // A full counter is ordinary backpressure. Invalid identity/sequence,
        // an issue after sealing, or an exhausted sequence is a protocol fault.
        if(issue_v && (!issue_match || !participants[issue_id] || sealed[issue_id] ||
            issue_seq!=issued[issue_id] || issued[issue_id]=={SEQ_W{1'b1}})) fault<=1;
        if(retire_v && !retire_ready) fault<=1;
        if(issue_v && issue_ready) begin
          issued[issue_id]<=issued[issue_id]+1'b1;
          outstanding[issue_id]<=outstanding[issue_id]+1'b1;
        end
        if(retire_v && retire_ready) begin
          retired[retire_id]<=retired[retire_id]+1'b1;
          outstanding[retire_id]<=outstanding[retire_id]-1'b1;
        end
        if(issue_v && issue_ready && retire_v && retire_ready && issue_id==retire_id)
          outstanding[issue_id]<=outstanding[issue_id];
        if(seal_v) begin
          if(seal_id>=N || seal_context!=context_q || seal_version!=version_q ||
             !active || !participants[seal_id] || sealed[seal_id] ||
             (issue_v && issue_id==seal_id)) fault<=1;
          else sealed[seal_id]<=1'b1;
        end
      end
    end
  end
endmodule

// Parallel per-recipient alternative: no scalar event serialization. Every
// input tuple retains its actual provenance; shared/current metadata is not
// substituted for a late event. Physical wide-face delivery is still required.
module ot_qwen_xdelivery_ack_vector #(
  parameter integer ENABLE=0, N=48, SEQ_W=40, COUNT_W=7
)(
  input wire clk,rst_n,begin_v,fenced_clear,
  input wire [15:0] begin_context, input wire [31:0] begin_version,
  input wire [N-1:0] participant_mask,
  input wire [N-1:0] issue_v, output wire [N-1:0] issue_ready,
  input wire [N*SEQ_W-1:0] issue_seq,
  input wire [N*16-1:0] issue_context, input wire [N*32-1:0] issue_version,
  input wire [N-1:0] retire_v, output wire [N-1:0] retire_ready,
  input wire [N*SEQ_W-1:0] retire_seq,
  input wire [N*16-1:0] retire_context, input wire [N*32-1:0] retire_version,
  input wire [N-1:0] seal_v,
  input wire [N*16-1:0] seal_context, input wire [N*32-1:0] seal_version,
  output wire drained,fault
);
  reg active,control_fault;
  reg [15:0] context_q; reg [31:0] version_q;
  reg [N-1:0] participants;
  wire [N-1:0] empty,recipient_fault;
  assign fault=control_fault || (|recipient_fault);
  assign drained=ENABLE && active && (&empty) && !fault;
  always @(posedge clk) begin
    if(!rst_n || fenced_clear) begin
      active<=0;control_fault<=0;context_q<=0;version_q<=0;participants<=0;
    end else if(ENABLE && begin_v) begin
      if((|issue_v) || (|retire_v) || (|seal_v)) control_fault<=1; // BEGIN_EVENT_FENCE_VECTOR
      else if(active && !drained) control_fault<=1;
      else begin active<=1;context_q<=begin_context;version_q<=begin_version;participants<=participant_mask;end
    end
  end
  for(genvar g=0;g<N;g=g+1) begin: recipient
    reg sealed,local_fault;
    reg [COUNT_W-1:0] outstanding;
    reg [SEQ_W-1:0] issued,retired;
    wire issue_match=ENABLE && active && issue_context[g*16+:16]==context_q &&
      issue_version[g*32+:32]==version_q;
    wire retire_match=ENABLE && active && retire_context[g*16+:16]==context_q &&
      retire_version[g*32+:32]==version_q;
    assign recipient_fault[g]=local_fault;
    assign empty[g]=!participants[g] || (sealed && outstanding==0);
    assign issue_ready[g]=issue_match && !fault && participants[g] && !sealed &&
      outstanding!={COUNT_W{1'b1}} && issued!={SEQ_W{1'b1}} && issue_seq[g*SEQ_W+:SEQ_W]==issued;
    assign retire_ready[g]=retire_match && !fault && participants[g] &&
      outstanding!=0 && retire_seq[g*SEQ_W+:SEQ_W]==retired;
    always @(posedge clk) begin
      if(!rst_n || fenced_clear) begin
        sealed<=0;local_fault<=0;outstanding<=0;issued<=0;retired<=0;
      end else if(ENABLE) begin
        if(begin_v && (!active || drained)) begin
          sealed<=0;outstanding<=0;issued<=0;retired<=0;
        end else if(!begin_v) begin
          if(issue_v[g] && (!issue_match || !participants[g] || sealed ||
             issue_seq[g*SEQ_W+:SEQ_W]!=issued || issued=={SEQ_W{1'b1}})) local_fault<=1;
          if(retire_v[g] && !retire_ready[g]) local_fault<=1;
          if(issue_v[g] && issue_ready[g]) begin issued<=issued+1'b1;outstanding<=outstanding+1'b1;end
          if(retire_v[g] && retire_ready[g]) begin retired<=retired+1'b1;outstanding<=outstanding-1'b1;end
          if(issue_v[g] && issue_ready[g] && retire_v[g] && retire_ready[g]) outstanding<=outstanding;
          if(seal_v[g]) begin
            if(!active || !participants[g] || sealed || issue_v[g] ||
               seal_context[g*16+:16]!=context_q || seal_version[g*32+:32]!=version_q) local_fault<=1;
            else sealed<=1;
          end
        end
      end
    end
  end
endmodule

// Allocation and VM reservation controller. The source owns version generation.
// acquire precedes publication; accepted_mask is the deduplicated actual tile
// op_accept set, not the offered GO bus. It must span every real participant.
module ot_qwen_xdelivery_lifetime_ctrl #(
  parameter integer ENABLE=0, TILES=768, BANKS=16, TOKEN_W=16
)(
  input wire clk, rst_n,
  input wire offer_v, output wire offer_ready,
  input wire [378:0] offer_ib, input wire offer_mode,
  input wire [TILES-1:0] offer_participants,
  output wire acquire_v, input wire acquire_ready,
  input wire [31:0] acquire_version,
  output reg [378:0] held_ib, output reg held_mode,
  output reg [TOKEN_W-1:0] held_context, output reg [31:0] held_version,
  output wire dispatch_v,
  input wire accept_v, input wire [$clog2(TILES)-1:0] accept_tile,
  input wire [TOKEN_W-1:0] accept_context, input wire [31:0] accept_version,
  input wire [378:0] accept_ib,
  output reg banks_begin,
  input wire [BANKS-1:0] bank_drained,
  input wire source_output_drained,
  output wire release_v, input wire release_ready,
  output wire flush_req, input wire transport_flush_ack,
  output reg fault
);
  localparam IDLE=0, ACQUIRE=1, DISPATCH=2, DRAIN=3, WRAP_FENCE=4, RESET_FENCE=5;
  reg [2:0] state;
  reg [TILES-1:0] participants, accepted;
  reg [TOKEN_W-1:0] next_context;
  assign offer_ready=ENABLE && state==IDLE && !fault;
  assign acquire_v=ENABLE && state==ACQUIRE && !fault;
  assign dispatch_v=ENABLE && state==DISPATCH && !fault;
  assign release_v=ENABLE && state==DRAIN && (&bank_drained) &&
    source_output_drained && !fault;
  assign flush_req=ENABLE && (state==WRAP_FENCE || state==RESET_FENCE);
  always @(posedge clk) begin
    if(!rst_n) begin
      state<=RESET_FENCE; next_context<=0; held_context<=0;
      held_version<=0; held_ib<=0; held_mode<=0;
      participants<=0; accepted<=0; banks_begin<=0; fault<=0;
    end else if(ENABLE) begin
      banks_begin<=0;
      if((state==RESET_FENCE || state==WRAP_FENCE) && transport_flush_ack) begin
        state<=IDLE; next_context<=0;
      end
      if(offer_v && offer_ready) begin
        held_ib<=offer_ib; held_mode<=offer_mode;
        participants<=offer_participants; accepted<=0;
        held_context<=next_context; state<=ACQUIRE;
      end
      if(acquire_v && acquire_ready) begin
        held_version<=acquire_version; banks_begin<=1; state<=DISPATCH;
      end
      if(accept_v) begin
        if(state!=DISPATCH || accept_tile>=TILES || !participants[accept_tile] ||
           accepted[accept_tile] || accept_context!=held_context ||
           accept_version!=held_version || accept_ib!=held_ib) fault<=1;
        else accepted[accept_tile]<=1'b1;
      end
      if(state==DISPATCH && (accepted & participants)==participants) state<=DRAIN;
      if(release_v && release_ready) begin
        if(next_context=={TOKEN_W{1'b1}}) state<=WRAP_FENCE;
        else begin next_context<=next_context+1'b1; state<=IDLE; end
      end
    end
  end
endmodule
