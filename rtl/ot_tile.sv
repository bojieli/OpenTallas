`timescale 1ns/1ps
// Requirement-traceable tile pipeline: route record -> immutable ROM read ->
// deterministic integer-DV MAC -> registered result.  Target MXFP4/FP8/BF16
// macro wrappers plug into the same metadata and poison boundaries.
module ot_tile #(
    parameter integer NUM_EXPERTS = 16,
    parameter integer TOP_K = 6,
    parameter integer WORDS_PER_EXPERT = 64,
    parameter integer LANES = 16,
    parameter integer ACT_W = 8,
    parameter integer WEIGHT_W = 4,
    parameter integer ACC_W = 32,
    parameter integer EXPERT_ID_W = 10,
    parameter INIT_FILE = ""
) (
    input  wire                                  clk,
    input  wire                                  rst_n,
    input  wire                                  route_valid,
    output wire                                  route_ready,
    input  wire [223:0]                          route_record,
    input  wire                                  act_valid,
    output wire                                  act_ready,
    input  wire [LANES*ACT_W-1:0]                act_payload,
    input  wire [$clog2(WORDS_PER_EXPERT)-1:0]    act_word_index,
    input  wire [15:0]                           act_transaction_id,
    input  wire [7:0]                            act_sequence,
    input  wire                                  act_last,
    input  wire                                  act_poison,
    output wire                                  result_valid,
    input  wire                                  result_ready,
    output wire signed [ACC_W-1:0]               result_sum,
    output wire [15:0]                           result_transaction_id,
    output wire [7:0]                            result_sequence,
    output wire                                  result_last,
    output wire                                  result_poison,
    output wire [3:0]                            result_status,
    output wire                                  route_bad_crc,
    output wire                                  route_bad_field
);
    localparam integer WORD_W = LANES * WEIGHT_W;
    localparam integer WORD_INDEX_W = (WORDS_PER_EXPERT <= 2) ? 1 : $clog2(WORDS_PER_EXPERT);
    wire ctx_valid;
    reg ctx_ready;
    wire [NUM_EXPERTS-1:0] ctx_mask;
    wire [15:0] ctx_txn;
    wire [7:0] ctx_epoch;
    wire [6:0] ctx_layer;
    wire [4:0] ctx_topk;
    wire ctx_poison;
    wire [15:0] ctx_dup;
    reg route_active;
    reg [NUM_EXPERTS-1:0] active_mask;
    reg [15:0] active_route_txn;
    reg active_route_poison;
    reg [LANES*ACT_W-1:0] act_d;
    reg [15:0] txn_d;
    reg [7:0] seq_d;
    reg last_d;
    reg poison_d;
    reg result_hold_valid;
    reg signed [ACC_W-1:0] result_hold_sum;
    reg [15:0] result_hold_txn;
    reg [7:0] result_hold_seq;
    reg result_hold_last;
    reg result_hold_poison;
    reg [3:0] result_hold_status;
    wire rom_valid;
    wire [NUM_EXPERTS*LANES*WEIGHT_W-1:0] rom_words;
    wire dot_valid;
    wire dot_poison;
    wire signed [ACC_W-1:0] dot_sum;
    wire [3:0] dot_status;
    wire act_fire = act_valid && act_ready;
    wire result_fire = result_valid && result_ready;

    ot_route_mask #(
        .NUM_EXPERTS(NUM_EXPERTS), .TOP_K(TOP_K), .EXPERT_ID_W(EXPERT_ID_W)
    ) route (
        .clk(clk), .rst_n(rst_n), .route_valid(route_valid), .route_ready(route_ready),
        .route_record(route_record), .ctx_valid(ctx_valid), .ctx_ready(ctx_ready),
        .ctx_mask(ctx_mask), .ctx_transaction_id(ctx_txn), .ctx_epoch_id(ctx_epoch),
        .ctx_layer_id(ctx_layer), .ctx_top_k_count(ctx_topk), .ctx_poison(ctx_poison),
        .ctx_duplicate_slots(ctx_dup), .bad_crc_seen(route_bad_crc),
        .bad_field_seen(route_bad_field)
    );

    // One fixed-latency ROM issue is allowed while the result register is
    // occupied.  A route context is retained until its terminal activation.
    always @* begin
        ctx_ready = !route_active;
    end
    assign act_ready = route_active && !result_hold_valid && !rom_valid;
    assign result_valid = result_hold_valid;
    assign result_sum = result_hold_sum;
    assign result_transaction_id = result_hold_txn;
    assign result_sequence = result_hold_seq;
    assign result_last = result_hold_last;
    assign result_poison = result_hold_poison;
    assign result_status = result_hold_status;

    via_mask_rom #(
        .NUM_EXPERTS(NUM_EXPERTS), .WORDS_PER_EXPERT(WORDS_PER_EXPERT),
        .LANES(LANES), .WEIGHT_W(WEIGHT_W), .WORD_INDEX_W(WORD_INDEX_W),
        .INIT_FILE(INIT_FILE)
    ) rom (
        .clk(clk), .rst_n(rst_n), .req_valid(act_fire), .expert_mask(active_mask),
        .word_index(act_word_index), .rsp_valid(rom_valid), .weight_words(rom_words)
    );

    ot_numeric_dot #(
        .NUM_EXPERTS(NUM_EXPERTS), .LANES(LANES), .ACT_W(ACT_W),
        .WEIGHT_W(WEIGHT_W), .ACC_W(ACC_W)
    ) dot (
        .clk(clk), .rst_n(rst_n), .in_valid(rom_valid), .in_poison(poison_d),
        .expert_enable(active_mask), .activations(act_d), .weights(rom_words),
        .out_valid(dot_valid), .out_poison(dot_poison), .result(dot_sum),
        .status(dot_status)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            route_active <= 1'b0;
            active_mask <= {NUM_EXPERTS{1'b0}};
            active_route_txn <= 0;
            active_route_poison <= 1'b0;
            act_d <= 0;
            txn_d <= 0;
            seq_d <= 0;
            last_d <= 1'b0;
            poison_d <= 1'b0;
            result_hold_valid <= 1'b0;
            result_hold_sum <= 0;
            result_hold_txn <= 0;
            result_hold_seq <= 0;
            result_hold_last <= 1'b0;
            result_hold_poison <= 1'b0;
            result_hold_status <= 0;
        end else begin
            if (ctx_valid && ctx_ready) begin
                route_active <= 1'b1;
                active_mask <= ctx_mask;
                active_route_txn <= ctx_txn;
                active_route_poison <= ctx_poison;
            end
            if (act_fire) begin
                act_d <= act_payload;
                txn_d <= act_transaction_id;
                seq_d <= act_sequence;
                last_d <= act_last;
                poison_d <= act_poison || active_route_poison ||
                            (act_transaction_id != active_route_txn);
            end
            if (dot_valid) begin
                result_hold_valid <= 1'b1;
                result_hold_sum <= dot_sum;
                result_hold_txn <= txn_d;
                result_hold_seq <= seq_d;
                result_hold_last <= last_d;
                result_hold_poison <= dot_poison;
                result_hold_status <= dot_status;
            end
            if (result_fire) begin
                result_hold_valid <= 1'b0;
                if (result_hold_last)
                    route_active <= 1'b0;
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (NUM_EXPERTS < 1 || NUM_EXPERTS > 1024 || TOP_K < 1 || TOP_K > 16)
            $error("ot_tile parameter outside architectural limit");
    end
`endif
endmodule
