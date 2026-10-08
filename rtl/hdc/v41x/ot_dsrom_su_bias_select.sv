`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM recovery lever "router_act" (default-off, new file): the router's `scores + bias` (ffn.bias) folded
// into the front of the adopted parallel top-6 (rtl/hdc/v41/ot_hdc_select_tree.sv, unchanged): one binary32
// add per lane (ot_hdc_qadd_lat #(KEEP 1, LAT LA); with the 1.2 GHz FILE SWAP rtl/hdc/ot_hdc_fastfp_lat_f12.sv
// LAT 4 is ot_hdc_fp32_add_f12_l4), the tree's input then the biased score -- tools/hdc_golden_v41
// add(scores, bias), RNE, canonical +0, the same rounding the stream unit's ffn.bias op does.  The bias is
// the layer's constant (a ROM beside the tree, in_bias lane l of beat b = bias[b*W + l]).  The unbiased
// scores stay where they are for ffn.weights.  Latency: the tree's + LA.
// ---------------------------------------------------------------------------
module ot_dsrom_su_bias_select #(
    parameter integer K     = 6,
    parameter integer VW    = 32,
    parameter integer IW    = 9,
    parameter integer W     = 64,
    parameter integer NB    = 8,
    parameter integer ORDER = 1,
    parameter integer LA    = 4
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    input  wire              in_last,
    input  wire [W-1:0]      in_lv,
    input  wire [W*32-1:0]   in_val,
    input  wire [W*32-1:0]   in_bias,
    input  wire [W*IW-1:0]   in_idx,
    output wire              out_valid,
    output wire [K-1:0]      out_v,
    output wire [K*IW-1:0]   out_idx,
    output wire [K-1:0]      out_ninf,
    output wire              out_fault
);
    wire [W*32-1:0] b_val;
    wire [W-1:0]    b_f;
    genvar l;
    generate
        for (l = 0; l < W; l = l + 1) begin : g_add
            ot_hdc_qadd_lat #(.KEEP(1), .LAT(LA)) u (clk, rst_n, in_valid && in_lv[l], in_val[32*l +: 32],
                                                     in_bias[32*l +: 32], b_val[32*l +: 32], b_f[l]);
        end
    endgenerate
    wire [LA:0] vd, ld;
    ot_hdc_vline #(.D(LA)) u_v (.clk(clk), .rst_n(rst_n), .v(in_valid), .vd(vd));
    ot_hdc_vline #(.D(LA)) u_l (.clk(clk), .rst_n(rst_n), .v(in_valid && in_last), .vd(ld));
    wire [W-1:0]    lv_d;
    wire [W*IW-1:0] idx_d;
    ot_hdc_delay #(.W(W), .D(LA)) d_lv (clk, rst_n, in_lv, lv_d);
    ot_hdc_delay #(.W(W * IW), .D(LA)) d_ix (clk, rst_n, in_idx, idx_d);
    reg fault_r;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault_r <= 1'b0; else if (|b_f) fault_r <= 1'b1;
    end
    assign out_fault = fault_r;
    ot_hdc_select_tree #(.K(K), .VW(VW), .IW(IW), .W(W), .NB(NB), .ORDER(ORDER)) u_t (
        .clk(clk), .rst_n(rst_n), .in_valid(vd[LA]), .in_last(ld[LA]), .in_lv(lv_d), .in_val(b_val),
        .in_idx(idx_d), .out_valid(out_valid), .out_v(out_v), .out_idx(out_idx), .out_ninf(out_ninf));
endmodule

// Fixed top for the screen (K 6, FP32, IW 9, W 64, NB 8, ascending order, LA 4).
module ot_dsrom_su_bias_select_top (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    input  wire              in_last,
    input  wire [63:0]       in_lv,
    input  wire [64*32-1:0]  in_val,
    input  wire [64*32-1:0]  in_bias,
    input  wire [64*9-1:0]   in_idx,
    output wire              out_valid,
    output wire [5:0]        out_v,
    output wire [6*9-1:0]    out_idx,
    output wire [5:0]        out_ninf,
    output wire              out_fault
);
    ot_dsrom_su_bias_select u (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_last(in_last), .in_lv(in_lv),
        .in_val(in_val), .in_bias(in_bias), .in_idx(in_idx), .out_valid(out_valid), .out_v(out_v),
        .out_idx(out_idx), .out_ninf(out_ninf), .out_fault(out_fault));
endmodule
