`timescale 1ns/1ps
// Small multi-block executable target for the independent Verilator/C++
// scoreboard.  This wrapper contains no behavior beyond DUT composition.
module ot_verilator_unit_top (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         dot_valid,
    input  wire         dot_poison,
    input  wire [1:0]   dot_enable,
    input  wire [15:0]  dot_activations,
    input  wire [31:0]  dot_weights,
    output wire         dot_out_valid,
    output wire         dot_out_poison,
    output wire [15:0]  dot_result,
    output wire [3:0]   dot_status,

    input  wire         skid_in_valid,
    output wire         skid_in_ready,
    input  wire [15:0]  skid_in_data,
    output wire         skid_out_valid,
    input  wire         skid_out_ready,
    output wire [15:0]  skid_out_data,
    output wire         skid_overflow,
    output wire         skid_underflow,

    input  wire         credit_reserve_valid,
    output wire         credit_reserve_ready,
    input  wire [2:0]   credit_reserve_mask,
    input  wire         credit_release_valid,
    input  wire [2:0]   credit_release_mask,
    output wire [8:0]   credit_free_count,
    output wire         credit_overflow_error,
    output wire         credit_underflow_error,
    output wire         credit_conservation_error
);
    ot_numeric_dot #(
        .NUM_EXPERTS(2), .LANES(2), .ACT_W(8), .WEIGHT_W(8), .ACC_W(16),
        .REPORT_SATURATION_RISK(0)
    ) dot (
        .clk(clk), .rst_n(rst_n), .in_valid(dot_valid),
        .in_poison(dot_poison), .expert_enable(dot_enable),
        .activations(dot_activations), .weights(dot_weights),
        .out_valid(dot_out_valid), .out_poison(dot_out_poison),
        .result(dot_result), .status(dot_status)
    );

    ot_skid_buffer #(.WIDTH(16), .DEPTH(2)) skid (
        .clk(clk), .rst_n(rst_n), .in_valid(skid_in_valid),
        .in_ready(skid_in_ready), .in_data(skid_in_data),
        .out_valid(skid_out_valid), .out_ready(skid_out_ready),
        .out_data(skid_out_data), .overflow(skid_overflow),
        .underflow(skid_underflow)
    );

    ot_credit_manager #(.SINKS(3), .DEPTH(4), .CREDIT_W(3)) credits (
        .clk(clk), .rst_n(rst_n), .reserve_valid(credit_reserve_valid),
        .reserve_ready(credit_reserve_ready), .reserve_mask(credit_reserve_mask),
        .release_valid(credit_release_valid), .release_mask(credit_release_mask),
        .free_count(credit_free_count), .overflow_error(credit_overflow_error),
        .underflow_error(credit_underflow_error),
        .conservation_error(credit_conservation_error)
    );
endmodule
