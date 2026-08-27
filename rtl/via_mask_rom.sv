`timescale 1ns/1ps
// Technology-independent behavioral contract for the via-programmed ROM macro.
//
// Physical implementation note: `mem` is replaced by a foundry ROM macro whose
// programming layer connects/omits the drain via. There is intentionally no
// write port. Expert weights are interleaved by word index so every cycle can
// engage lanes across the full macro. `expert_mask` is the wordline mask.
module via_mask_rom #(
    parameter integer NUM_EXPERTS = 4,
    parameter integer WORDS_PER_EXPERT = 4,
    parameter integer LANES = 4,
    parameter integer WEIGHT_W = 8,
    parameter integer WORD_INDEX_W = $clog2(WORDS_PER_EXPERT),
    parameter INIT_FILE = ""
) (
    input  wire                                      clk,
    input  wire                                      rst_n,
    input  wire                                      req_valid,
    input  wire [NUM_EXPERTS-1:0]                    expert_mask,
    input  wire [WORD_INDEX_W-1:0]                   word_index,
    output reg                                       rsp_valid,
    output reg  [NUM_EXPERTS*LANES*WEIGHT_W-1:0]     weight_words
);
    localparam integer WORD_W = LANES * WEIGHT_W;
    localparam integer DEPTH = NUM_EXPERTS * WORDS_PER_EXPERT;
    reg [WORD_W-1:0] mem [0:DEPTH-1];
    integer expert;

    initial begin
        if (INIT_FILE != "")
            $readmemh(INIT_FILE, mem);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rsp_valid <= 1'b0;
            weight_words <= {NUM_EXPERTS*LANES*WEIGHT_W{1'b0}};
        end else begin
            rsp_valid <= req_valid;
            if (req_valid) begin
                // Interleaved address: all experts for word i are adjacent. The
                // physical macro banks these addresses so selected wordlines
                // evaluate in parallel across the full array.
                for (expert = 0; expert < NUM_EXPERTS; expert = expert + 1) begin
                    if (expert_mask[expert])
                        weight_words[expert*WORD_W +: WORD_W]
                            <= mem[word_index*NUM_EXPERTS + expert];
                    else
                        weight_words[expert*WORD_W +: WORD_W]
                            <= {WORD_W{1'b0}};
                end
            end else begin
                weight_words <= {NUM_EXPERTS*LANES*WEIGHT_W{1'b0}};
            end
        end
    end
endmodule
