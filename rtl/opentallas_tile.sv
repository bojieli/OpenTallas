// Two-stage ROM-read/MAC pipeline demonstrating wordline-masked MoE execution.
module opentallas_tile #(
    parameter integer NUM_EXPERTS = 4,
    parameter integer TOP_K = 2,
    parameter integer WORDS_PER_EXPERT = 4,
    parameter integer LANES = 4,
    parameter integer ACT_W = 8,
    parameter integer WEIGHT_W = 8,
    parameter integer ACC_W = 32,
    parameter integer EXPERT_ID_W = $clog2(NUM_EXPERTS),
    parameter integer WORD_INDEX_W = $clog2(WORDS_PER_EXPERT),
    parameter INIT_FILE = ""
) (
    input  wire                              clk,
    input  wire                              rst_n,
    input  wire                              in_valid,
    input  wire [TOP_K*EXPERT_ID_W-1:0]      selected_expert_ids,
    input  wire [TOP_K-1:0]                  selected_valid,
    input  wire [WORD_INDEX_W-1:0]           word_index,
    input  wire [LANES*ACT_W-1:0]            activations,
    output wire                              out_valid,
    output wire signed [ACC_W-1:0]           partial_sum
);
    wire [NUM_EXPERTS-1:0] expert_mask;
    wire rom_valid;
    wire [NUM_EXPERTS*LANES*WEIGHT_W-1:0] rom_weights;
    reg [LANES*ACT_W-1:0] activations_d;

    expert_mask_controller #(
        .NUM_EXPERTS(NUM_EXPERTS),
        .TOP_K(TOP_K),
        .EXPERT_ID_W(EXPERT_ID_W)
    ) mask_controller (
        .selected_expert_ids(selected_expert_ids),
        .selected_valid(selected_valid),
        .expert_mask(expert_mask)
    );

    via_mask_rom #(
        .NUM_EXPERTS(NUM_EXPERTS),
        .WORDS_PER_EXPERT(WORDS_PER_EXPERT),
        .LANES(LANES),
        .WEIGHT_W(WEIGHT_W),
        .WORD_INDEX_W(WORD_INDEX_W),
        .INIT_FILE(INIT_FILE)
    ) weight_rom (
        .clk(clk),
        .rst_n(rst_n),
        .req_valid(in_valid),
        .expert_mask(expert_mask),
        .word_index(word_index),
        .rsp_valid(rom_valid),
        .weight_words(rom_weights)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            activations_d <= {LANES*ACT_W{1'b0}};
        else if (in_valid)
            activations_d <= activations;
    end

    rom_mac_tile #(
        .NUM_EXPERTS(NUM_EXPERTS),
        .LANES(LANES),
        .ACT_W(ACT_W),
        .WEIGHT_W(WEIGHT_W),
        .ACC_W(ACC_W)
    ) mac (
        .clk(clk),
        .rst_n(rst_n),
        .in_valid(rom_valid),
        .activations(activations_d),
        .weight_words(rom_weights),
        .out_valid(out_valid),
        .partial_sum(partial_sum)
    );
endmodule
