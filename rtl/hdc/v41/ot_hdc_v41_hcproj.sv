`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hyper-connection projection engine (HE) of the DeepSeek-V4.1 decode core.
//
// The mixes of a hyper-connection are an FP32-weight matrix-vector product
// (tools/hdc_golden_v41.py Model.hc_mixes: matvec_fp32(fn, flat), fn [24, 640]
// binary32), sequential over K from +0 per output.  Every other matrix of the
// model is BF16 or block-quantised, so the shared BF16 matrix engine keeps its
// exact BF16 multipliers and these projections get this small engine of their
// own, which runs BESIDE the matrix engine: a sublayer's attention or MoE work
// proceeds while its mixes accumulate.
//
// NL lanes x IL interleaved outputs, the matrix engine's lane structure: each
// lane is the qualified binary32 multiplier (ot_hdc_fmul) feeding the qualified
// adder (ot_hdc_fadd), whose sum circulates back exactly IL cycles later, so
// every output accumulates its products strictly in order while the lane
// retires one multiply-accumulate per cycle.  Element order: k, then slot j;
// lane l of slot j is row j*NL + l; its weight is lane l of word
// wbase + k*IL + j; x[k] is one vector-memory element, broadcast.  After the
// last k, slot j's NL results are written as one masked word at obase + j*NL.
// Latency is dominated by the dependence chain the specification fixes:
// K * IL cycles for up to NL*IL outputs.
// ---------------------------------------------------------------------------
module ot_hdc_v41_hcproj #(
    parameter integer NL = 3,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_k,
    input  wire [AW-1:0]     i_wbase,
    input  wire [AW-1:0]     i_xbase,
    input  wire [AW-1:0]     i_obase,
    output reg               hr_re,
    output reg  [AW-1:0]     hr_addr,
    input  wire [NL*32-1:0]  hr_q,
    output reg               x_re,
    output reg  [AW-1:0]     x_addr,
    input  wire [31:0]       x_q,
    output reg               o_we,
    output reg  [AW-1:0]     o_addr,
    output reg  [31:0]       o_mask,
    output reg  [1023:0]     o_data,
    output reg               fault
);
    localparam integer PW = $clog2(IL);
    reg              active;
    reg [NW-1:0]     k, k_r, nout;
    reg [PW-1:0]     j;
    reg [AW-1:0]     cur, xk, obase;
    assign ready = !active;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; hr_re <= 1'b0; x_re <= 1'b0;
        end else begin
            hr_re <= active; x_re <= active;
            if (!active) begin
                if (go) begin
                    active <= 1'b1; k <= 0; j <= 0; k_r <= i_k; nout <= i_nout;
                    cur <= i_wbase; xk <= i_xbase; obase <= i_obase;
                end
            end else begin
                cur <= cur + 1'b1;
                j <= j + 1'b1;
                if (j == IL - 1) begin
                    j <= 0; xk <= xk + 1'b1; k <= k + 1'b1;
                    if (k + 1 == k_r) active <= 1'b0;
                end
            end
        end
    end
    // issue tags (registered with the addresses)
    reg          e_v, e_first, e_last;
    reg [PW-1:0] e_j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) e_v <= 1'b0; else e_v <= active;
    end
    always @(posedge clk) begin
        hr_addr <= cur; x_addr <= xk;
        e_first <= (k == 0); e_last <= (k + 1 == k_r); e_j <= j;
    end
    // s1: memories answer; s2: operands captured
    reg          s1_v, s2_v, s1_first, s2_first, s1_last, s2_last;
    reg [PW-1:0] s1_j, s2_j;
    reg [NL*32-1:0] s2_w;
    reg [31:0]   s2_x;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s2_v <= 1'b0; end
        else begin s1_v <= e_v; s2_v <= s1_v; end
    end
    always @(posedge clk) begin
        s1_first <= e_first; s1_last <= e_last; s1_j <= e_j;
        s2_first <= s1_first; s2_last <= s1_last; s2_j <= s1_j;
        s2_w <= hr_q; s2_x <= x_q;
    end
    // tags across the multiplier (5) and the adder (5)
    wire [5:0] vm;
    ot_hdc_vline #(.D(5)) u_vm (.clk(clk), .rst_n(rst_n), .v(s2_v), .vd(vm));
    wire m_first, m_last;
    wire [PW-1:0] m_j;
    ot_hdc_delay #(.W(2 + PW), .D(5)) u_tm (.clk(clk), .rst_n(rst_n), .d({s2_first, s2_last, s2_j}),
                                           .q({m_first, m_last, m_j}));
    wire [5:0] va;
    ot_hdc_vline #(.D(5)) u_va (.clk(clk), .rst_n(rst_n), .v(vm[5]), .vd(va));
    wire a_last;
    wire [PW-1:0] a_j;
    ot_hdc_delay #(.W(1 + PW), .D(5)) u_ta (.clk(clk), .rst_n(rst_n), .d({m_last, m_j}), .q({a_last, a_j}));
    wire [NL*32-1:0] sum;
    wire [NL-1:0] lf;
    genvar l;
    generate
        for (l = 0; l < NL; l = l + 1) begin : g_lane
            wire [31:0] prod, fb;
            wire f0, f1;
            ot_hdc_fmul u_mul (clk, rst_n, s2_v, s2_w[32*l +: 32], s2_x, prod, f0);
            //: the sum of slot j re-enters exactly IL cycles after it left the adder's input
            ot_hdc_fadd u_add (clk, rst_n, vm[5], m_first ? 32'd0 : fb, prod, sum[32*l +: 32], f1);
            ot_hdc_delay #(.W(32), .D(IL - 5)) u_fb (.clk(clk), .rst_n(rst_n), .d(sum[32*l +: 32]), .q(fb));
            assign lf[l] = f0 | f1;
        end
    endgenerate
    integer q;
    wire [1023:0] sum_pad = {{(1024 - NL*32){1'b0}}, sum};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_we <= 1'b0; else o_we <= va[5] && a_last;
    end
    always @(posedge clk) begin
        o_addr <= obase + a_j * NL;
        for (q = 0; q < 32; q = q + 1) begin
            o_mask[q] <= (q < NL) && ({{(32-PW){1'b0}}, a_j} * NL + q < nout);
            o_data[32*q +: 32] <= sum_pad[32*q +: 32];
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin idle <= 1'b1; fault <= 1'b0; end
        else begin
            idle <= !active && !go && !e_v && !s1_v && !s2_v && !(|vm) && !(|va) && !o_we;
            fault <= |lf;
        end
    end
endmodule
