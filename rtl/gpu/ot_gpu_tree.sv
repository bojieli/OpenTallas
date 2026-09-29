`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Fixed pairwise FP32 RNE reduction tree of an exact tensor-core column
// (docs/MICROARCH_MODEL.md, GPU-organised HBM comparators).
//
// N leaves (a power of two) enter together; level k adds leaf pairs
// (2i, 2i+1) of level k-1 with the qualified binary32 adder (ot_hdc_fadd,
// LATENCY 5, RNE, gradual underflow, canonical +0).  This is exactly the
// golden's pairwise tree  ((c0 + c1) + (c2 + c3)) + ...  over N aligned chunk
// sums (tools/hdc_golden.py matvec, tools/hdc_golden_v41.py csum).  A leaf
// the op does not use carries +0, which is the golden's +0 padding: the
// adder's zero bypass makes x + (+0) = x bit for bit.
//
// One vector per cycle; LATENCY = 5 * log2(N).  `tag` travels with the sum.
// ---------------------------------------------------------------------------
module ot_gpu_tree #(
    parameter integer N    = 32,
    parameter integer TAGW = 8
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            v,
    input  wire [N*32-1:0] d,
    input  wire [TAGW-1:0] tag,
    output wire            ov,
    output wire [31:0]     y,
    output wire [TAGW-1:0] otag,
    output wire            fault
);
    localparam integer LEV = (N <= 1) ? 0 : $clog2(N);
    // level lv occupies node indices [base(lv), base(lv) + (N >> lv)); base(lv) = 2N - 2(N >> lv)
    wire [(2*N-1)*32-1:0] nodes;
    wire [(N > 1 ? N-1 : 1)-1:0] nf;
    assign nodes[N*32-1:0] = d;
    localparam integer VD = (LEV > 0) ? 5*LEV : 2;
    wire [VD:0] vl;
    ot_hdc_vline #(.D(VD)) u_v (.clk(clk), .rst_n(rst_n), .v(v), .vd(vl));
    genvar lv, i;
    generate
        for (lv = 0; lv < LEV; lv = lv + 1) begin : g_lv
            for (i = 0; i < (N >> (lv + 1)); i = i + 1) begin : g_add
                wire [31:0] a = nodes[(2*N - 2*(N >> lv) + 2*i) * 32 +: 32];
                wire [31:0] b = nodes[(2*N - 2*(N >> lv) + 2*i + 1) * 32 +: 32];
                ot_hdc_fadd u_add (.clk(clk), .rst_n(rst_n), .v(vl[5*lv]), .a(a), .b(b),
                                   .y(nodes[(2*N - 2*(N >> (lv + 1)) + i) * 32 +: 32]),
                                   .fault(nf[(N - (N >> lv)) + i]));
            end
        end
    endgenerate
    ot_hdc_delay #(.W(TAGW), .D(5*LEV)) u_tag (.clk(clk), .rst_n(rst_n), .d(tag), .q(otag));
    assign ov = (LEV > 0) ? vl[5*LEV] : v;
    assign y = nodes[(2*N-2)*32 +: 32];
    assign fault = (LEV > 0) ? |nf : 1'b0;
endmodule
