// Distinct default-off candidate. Initialization receipts must come from real
// bank state after BEGIN; no timer or offered metadata substitutes them.
// Receipt ports are synchronous logical seams; transport and per-child clocks unbound.
module ot_qwen_xdelivery_lifetime_init_ctrl #(
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
  output wire [TILES-1:0] held_participants,
  output wire dispatch_v,
  input wire accept_v, input wire [$clog2(TILES)-1:0] accept_tile,
  input wire [TOKEN_W-1:0] accept_context, input wire [31:0] accept_version,
  input wire [378:0] accept_ib,
  output reg banks_begin,
  input wire [BANKS-1:0] bank_drained,
  input wire [BANKS-1:0] bank_init_v,
  output wire [BANKS-1:0] bank_init_ack,
  input wire [BANKS*TOKEN_W-1:0] bank_init_context,
  input wire [BANKS*32-1:0] bank_init_version,
  input wire [TILES-1:0] bank_init_participants,
  input wire source_output_drained,
  output wire release_v, input wire release_ready,
  output wire flush_req, input wire transport_flush_ack,
  output reg fault
);
  localparam IDLE=0, ACQUIRE=1, DISPATCH=2, DRAIN=3, WRAP_FENCE=4, RESET_FENCE=5, INIT_WAIT=6;
  reg [2:0] state;
  reg [TILES-1:0] participants, accepted;
  reg [TOKEN_W-1:0] next_context;
  reg [BANKS-1:0] initialized;
  assign bank_init_ack={BANKS{ENABLE && state==INIT_WAIT && !fault}} & bank_init_v;
  assign held_participants=participants;
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
      participants<=0; accepted<=0; initialized<=0; banks_begin<=0; fault<=0;
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
        held_version<=acquire_version; initialized<=0; banks_begin<=1; state<=INIT_WAIT;
      end
      for(integer b=0;b<BANKS;b=b+1) begin
        if(bank_init_v[b]) begin
          if(state!=INIT_WAIT || bank_init_context[b*TOKEN_W+:TOKEN_W]!=held_context ||
             bank_init_version[b*32+:32]!=held_version ||
             bank_init_participants[b*(TILES/BANKS)+:(TILES/BANKS)]!=participants[b*(TILES/BANKS)+:(TILES/BANKS)]) fault<=1; // INIT_IDENTITY_CHECK
          else initialized[b]<=1;
        end
      end
      if(state==INIT_WAIT && (&initialized) && !fault) state<=DISPATCH; // INIT_BARRIER
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

// Receipt is exposed only after the underlying vector bank BEGIN clock edge.
// A BEGIN/event collision faults that actual bank and suppresses the receipt.
module ot_qwen_xdelivery_ack_vector_init #(
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
  output wire drained,fault,
  output wire begin_ready, output wire init_v, input wire init_ack,
  output reg [15:0] init_context, output reg [31:0] init_version,
  output reg [N-1:0] init_participants
);
  reg initialized,pending;
  wire bank_begin=begin_v && begin_ready;
  assign begin_ready=ENABLE && !pending && (!initialized || drained) && !fault;
  assign init_v=ENABLE && pending && !fault;
  ot_qwen_xdelivery_ack_vector #(.ENABLE(ENABLE),.N(N),.SEQ_W(SEQ_W),.COUNT_W(COUNT_W)) bank(
    .begin_v(bank_begin),
    .clk(clk),
    .rst_n(rst_n),
    .fenced_clear(fenced_clear),
    .begin_context(begin_context),
    .begin_version(begin_version),
    .participant_mask(participant_mask),
    .issue_v(issue_v),
    .issue_ready(issue_ready),
    .issue_seq(issue_seq),
    .issue_context(issue_context),
    .issue_version(issue_version),
    .retire_v(retire_v),
    .retire_ready(retire_ready),
    .retire_seq(retire_seq),
    .retire_context(retire_context),
    .retire_version(retire_version),
    .seal_v(seal_v),
    .seal_context(seal_context),
    .seal_version(seal_version),
    .drained(drained),
    .fault(fault)
  );
  always @(posedge clk) begin
    if(!rst_n || fenced_clear) begin
      initialized<=0;pending<=0;init_context<=0;init_version<=0;init_participants<=0;
    end else if(ENABLE) begin
      if(init_v && init_ack) pending<=0;
      if(bank_begin) begin
        initialized<=1;pending<=1;init_context<=begin_context;init_version<=begin_version;init_participants<=participant_mask;
      end
    end
  end
endmodule
