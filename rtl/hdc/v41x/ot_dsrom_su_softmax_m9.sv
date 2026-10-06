`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Margin primitives for the fused softmax (ot_dsrom_su_softmax MARGIN build, owner margin-first rule 2026-10-06:
// block SS setup >= +40/+60 ps at 0.833 ns, so every stage of the f12 units that sat within ~50 ps is cut now).
// Same function, bit for bit, as every other cut set of ot_hdc_fp32_add_f12 / ot_hdc_fp32_mul_f12
// (rtl/hdc/ot_hdc_fp32_f12.sv, unchanged); only register boundaries move.
//   ot_dsrom_su_softmax_add9: an input register (operands from another unit own a stage) + all seven adder cuts
//                             (CUTS 7'b1111111): LAT 9.  x6u40 classes closed by it: k1->k3 (+16..+45 ps),
//                             k3->k5 (+32), first-stage paths fed from another unit (mbn +24, es_d +40, m1.y +32).
//   ot_dsrom_su_softmax_mul9: all eight multiplier cuts (CUTS 8'b11111111): LAT 9.  x6u40 classes: k1->k3 (+12),
//                             k3->k5 (+37), k6->y (+43).
//   ot_dsrom_su_softmax_mul #(LM): LM 9 -> mul9, otherwise ot_hdc_qmul_lat #(LM) (the earlier builds).
// ---------------------------------------------------------------------------
module ot_dsrom_su_softmax_add9 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire [1:0]  err,
    output wire        valid_out
);
    reg        v_i;
    reg [31:0] a_i, b_i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v_i <= 1'b0;
        else v_i <= valid_in;
    end
    always @(posedge clk) begin a_i <= a; b_i <= b; end
    ot_hdc_fp32_add_f12 #(.CUTS(7'b1111111)) u (.clk(clk), .rst_n(rst_n), .valid_in(v_i), .a(a_i), .b(b_i), .y(y),
                                                .err(err), .valid_out(valid_out));
endmodule

module ot_dsrom_su_softmax_mul9 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire [1:0]  err,
    output wire        valid_out
);
    ot_hdc_fp32_mul_f12 #(.CUTS(8'b11111111)) u (.*);
endmodule

module ot_dsrom_su_softmax_mul #(
    parameter integer LM = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    generate if (LM == 9) begin : g_m9
        wire [1:0] err;
        wire       vo;
        ot_dsrom_su_softmax_mul9 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                    .valid_out(vo));
        assign fault = vo && (err != 2'd0);    // ot_hdc_qmul_lat's convention
    end else begin : g_q
        ot_hdc_qmul_lat #(LM) u (clk, rst_n, v, a, b, y, fault);
    end endgenerate
endmodule
