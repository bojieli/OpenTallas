`timescale 1ns/1ps
// Exact signed-integer DV dot product with deterministic expert/lane order.
// The same transaction/poison/status contract is used by target-format macro
// wrappers, making this inexpensive block useful for control, RAS, and formal
// verification before qualified arithmetic macros are available.
module ot_numeric_dot #(
    parameter integer NUM_EXPERTS = 16,
    parameter integer LANES = 16,
    parameter integer ACT_W = 8,
    parameter integer WEIGHT_W = 4,
    parameter integer ACC_W = 32
) (
    input  wire                                  clk,
    input  wire                                  rst_n,
    input  wire                                  in_valid,
    input  wire                                  in_poison,
    input  wire [NUM_EXPERTS-1:0]                expert_enable,
    input  wire [LANES*ACT_W-1:0]                activations,
    input  wire [NUM_EXPERTS*LANES*WEIGHT_W-1:0] weights,
    output reg                                   out_valid,
    output reg                                   out_poison,
    output reg signed [ACC_W-1:0]                result,
    output reg [3:0]                             status
);
    localparam integer TERMS = NUM_EXPERTS * LANES;
    localparam integer TERM_W = ACT_W + WEIGHT_W + $clog2(TERMS + 1) + 2;
    localparam integer SUM_W = (ACC_W > TERM_W) ? ACC_W : TERM_W;
    localparam signed [ACC_W-1:0] ACC_MAX = {1'b0,{(ACC_W-1){1'b1}}};
    localparam signed [ACC_W-1:0] ACC_MIN = {1'b1,{(ACC_W-1){1'b0}}};
    integer e;
    integer l;
    reg signed [SUM_W-1:0] sum_comb;
    reg signed [ACT_W-1:0] a;
    reg signed [WEIGHT_W-1:0] w;
    reg signed [ACT_W+WEIGHT_W-1:0] product;
    reg signed [SUM_W-1:0] max_acc;
    reg signed [SUM_W-1:0] min_acc;
    reg sat_comb;
    reg signed [ACC_W-1:0] result_comb;

    always @* begin
        sum_comb = {SUM_W{1'b0}};
        a = {ACT_W{1'b0}};
        w = {WEIGHT_W{1'b0}};
        product = {(ACT_W+WEIGHT_W){1'b0}};
        for (e = 0; e < NUM_EXPERTS; e = e + 1) begin
            for (l = 0; l < LANES; l = l + 1) begin
                a = $signed(activations[l*ACT_W +: ACT_W]);
                w = $signed(weights[(e*LANES+l)*WEIGHT_W +: WEIGHT_W]);
                product = a * w;
                if (expert_enable[e])
                    sum_comb = sum_comb + product;
            end
        end
        max_acc = ACC_MAX;
        min_acc = ACC_MIN;
        sat_comb = 1'b0;
        if (sum_comb > max_acc) begin
            result_comb = max_acc[ACC_W-1:0];
            sat_comb = 1'b1;
        end else if (sum_comb < min_acc) begin
            result_comb = min_acc[ACC_W-1:0];
            sat_comb = 1'b1;
        end else begin
            result_comb = sum_comb[ACC_W-1:0];
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            out_poison <= 1'b0;
            result <= {ACC_W{1'b0}};
            status <= 4'b0;
        end else begin
            out_valid <= in_valid;
            out_poison <= in_poison;
            if (in_valid) begin
                result <= in_poison ? {ACC_W{1'b0}} : result_comb;
                status <= {in_poison, sat_comb, 2'b00};
            end else begin
                result <= {ACC_W{1'b0}};
                status <= 4'b0;
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (NUM_EXPERTS < 1 || LANES < 1 || ACT_W < 1 || WEIGHT_W < 1)
            $error("ot_numeric_dot has an illegal zero dimension");
        if (ACC_W < ACT_W + WEIGHT_W + $clog2(NUM_EXPERTS*LANES+1))
            $warning("ot_numeric_dot ACC_W may saturate configured term bound");
    end
`endif
endmodule
