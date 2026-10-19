`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// SIZING-ONLY P-lane variants of the d4g SM leaf matrix datapath (HBM-MTP / MTP-AREA, 2026-10-18; NOT bound into any die,
// no physical view, owner decides after deliverable 1).
//
// ot_hbm_sm_bdc_p: the production block-dot column ot_hbm_accel_smh_bdc (pin flops + ot_hbm_accel_smh_bd_col: LBS=2 x
//   ot_hbm_accel_bterm3 32-term FP8/FP4 block terms, LAT-7 FP32 ring accumulator with IL=8 interleaved rows, 2-input
//   tree) with ONE weight word broadcast to P activation/accumulator lanes.  Every lane is an unmodified copy of the
//   production ot_hbm_accel_smh_bd_col fed the SAME weight / control pin flops and its OWN activation pin flops, so lane p
//   computes bit-for-bit what the single-lane column computes on (w, x_p): same products, same carry-save sum, same two
//   roundings, same per-chunk ring accumulation order and tree order (no reordering across lanes).  Weight-only logic
//   (pin flops, E2M1 decode, weight significand fields, valid / first / last / tag pipes) is identical across lanes; the
//   flattening synthesis shares it (opt_merge), as a P-lane design would.
// ot_hbm_sm_tcc_p: the same for the BF16 column ot_hbm_accel_smh_tcc (two 8-lane tcl halves + the 16-lane tct tree).
// P = 1 is the current single-lane tile (same pins, same netlist).  Pin-registered boundary: every input lands in a pin
// flop (inside each column, as the production tile), every output leaves a flop; fault is the OR of the lanes' fault
// flops re-registered.  Static schedule only: no handshake.
// MUT (bench negative control only): 1 = lane P-1 reads lane 0's activation (lane alias).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_sm_bdc_p #(
    parameter integer P = 1, parameter integer LBS = 2, parameter integer IL = 8, parameter integer TAGW = 16,
    parameter integer MUT = 0
) (
    input  wire clk, input wire rst_a,
    input  wire i_v, input wire i_first, input wire i_last, input wire i_fp4, input wire [TAGW-1:0] i_tag,
    input  wire [LBS*266-1:0]   i_w,
    input  wire [P*LBS*266-1:0] i_x,
    output wire ov, output wire [P*32-1:0] y, output wire [TAGW-1:0] otag, output wire fault
);
    localparam integer XB = LBS * 266;
    wire [P-1:0] l_ov, l_fault;
    wire [P*TAGW-1:0] l_tag;
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_lane
        localparam integer SRC = (MUT == 1 && p == P - 1 && P > 1) ? 0 : p;
        ot_hbm_accel_smh_bdc #(.LBS(LBS), .IL(IL), .TAGW(TAGW)) u_l (
            .clk(clk), .rst_a(rst_a), .i_v(i_v), .i_first(i_first), .i_last(i_last), .i_fp4(i_fp4), .i_tag(i_tag),
            .i_w(i_w), .i_x(i_x[SRC*XB +: XB]),
            .ov(l_ov[p]), .y(y[32*p +: 32]), .otag(l_tag[TAGW*p +: TAGW]), .fault(l_fault[p]));
    end endgenerate
    assign ov = l_ov[0];
    assign otag = l_tag[0 +: TAGW];
    generate if (P == 1) begin : g_f1
        assign fault = l_fault[0];
    end else begin : g_fp
        reg fq;
        always @(posedge clk) fq <= |l_fault;
        assign fault = fq;
    end endgenerate
endmodule

module ot_hbm_sm_tcc_p #(
    parameter integer P = 1, parameter integer TAGW = 16, parameter integer MUT = 0
) (
    input  wire clk, input wire rst_a,
    input  wire i_v, input wire i_first, input wire i_last, input wire [TAGW-1:0] i_tag,
    input  wire [255:0]   i_w,
    input  wire [P*256-1:0] i_x,
    output wire ov, output wire [P*32-1:0] y, output wire [TAGW-1:0] otag, output wire fault
);
    wire [P-1:0] l_ov, l_fault;
    wire [P*TAGW-1:0] l_tag;
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_lane
        localparam integer SRC = (MUT == 1 && p == P - 1 && P > 1) ? 0 : p;
        ot_hbm_accel_smh_tcc #(.TAGW(TAGW)) u_l (
            .clk(clk), .rst_a(rst_a), .i_v(i_v), .i_first(i_first), .i_last(i_last), .i_tag(i_tag),
            .i_w(i_w), .i_x(i_x[SRC*256 +: 256]),
            .ov(l_ov[p]), .y(y[32*p +: 32]), .otag(l_tag[TAGW*p +: TAGW]), .fault(l_fault[p]));
    end endgenerate
    assign ov = l_ov[0];
    assign otag = l_tag[0 +: TAGW];
    generate if (P == 1) begin : g_f1
        assign fault = l_fault[0];
    end else begin : g_fp
        reg fq;
        always @(posedge clk) fq <= |l_fault;
        assign fault = fq;
    end endgenerate
endmodule
`default_nettype wire
