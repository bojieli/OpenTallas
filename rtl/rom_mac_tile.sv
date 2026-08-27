// Signed dot-product reduction for all wordline-selected expert words.
module rom_mac_tile #(
    parameter integer NUM_EXPERTS = 4,
    parameter integer LANES = 4,
    parameter integer ACT_W = 8,
    parameter integer WEIGHT_W = 8,
    parameter integer ACC_W = 32
) (
    input  wire                                  clk,
    input  wire                                  rst_n,
    input  wire                                  in_valid,
    input  wire [LANES*ACT_W-1:0]                activations,
    input  wire [NUM_EXPERTS*LANES*WEIGHT_W-1:0] weight_words,
    output reg                                   out_valid,
    output reg signed [ACC_W-1:0]                partial_sum
);
    integer expert;
    integer lane;
    reg signed [ACC_W-1:0] sum_comb;
    reg signed [ACT_W-1:0] activation_value;
    reg signed [WEIGHT_W-1:0] weight_value;

    always @* begin
        sum_comb = {ACC_W{1'b0}};
        activation_value = {ACT_W{1'b0}};
        weight_value = {WEIGHT_W{1'b0}};
        for (expert = 0; expert < NUM_EXPERTS; expert = expert + 1) begin
            for (lane = 0; lane < LANES; lane = lane + 1) begin
                activation_value = activations[lane*ACT_W +: ACT_W];
                weight_value = weight_words[(expert*LANES+lane)*WEIGHT_W +: WEIGHT_W];
                sum_comb = sum_comb + activation_value * weight_value;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            partial_sum <= {ACC_W{1'b0}};
        end else begin
            out_valid <= in_valid;
            if (in_valid)
                partial_sum <= sum_comb;
            else
                partial_sum <= {ACC_W{1'b0}};
        end
    end
endmodule
