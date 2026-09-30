`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 IN-CONTEXT vehicle for the shared FP32 primitives (ot_hdc_fp32_add_lat / ot_hdc_fp32_mul_lat): a column of
// NL multiply-accumulate lanes, each a multiply followed by an accumulate chain, and a pairwise add tree over the
// lanes -- the shape of a chunk8 dot (attention tile chunk, indexer head sum) -- with operand muxing and
// registered I/O around the units, so synthesis optimises the units inside a real parent (the primitives are
// not I/O-bounded as in a standalone route).  Each lane's operands come through a small select (as the lanes'
// own operand muxes do), the accumulator feeds back through a register, and every output is registered.
// Arithmetic is not checked here (the units are proven bit-identical separately); this is a timing vehicle.
// ---------------------------------------------------------------------------
module ot_hdc_fp_ctx #(
    parameter integer AL = 7,          // add latency
    parameter integer ML = 6,          // mul latency
    parameter integer NL = 8           // lanes (power of two)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire [1:0]        sel,
    input  wire [NL*32-1:0]  xa, xb, xc,
    output reg  [31:0]       y,
    output reg               fault
);
    localparam integer LG = $clog2(NL);
    reg [NL*32-1:0] ra, rb, rc;
    reg [1:0] rs;
    reg rv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rv <= 1'b0; else rv <= v;
    end
    always @(posedge clk) begin ra <= xa; rb <= xb; rc <= xc; rs <= sel; end
    wire [NL*32-1:0] prod, acc_q;
    wire [NL-1:0] pv, av;
    wire [NL*2-1:0] pe, ae;
    genvar i, l;
    generate for (i = 0; i < NL; i = i + 1) begin : g_lane
        wire [31:0] opa = rs[0] ? rc[32*i +: 32] : ra[32*i +: 32];
        wire [31:0] opb = rs[1] ? ra[32*i +: 32] : rb[32*i +: 32];
        ot_hdc_fp32_mul_lat #(.LAT(ML)) u_m (.clk(clk), .rst_n(rst_n), .valid_in(rv), .a(opa), .b(opb),
            .y(prod[32*i +: 32]), .err(pe[2*i +: 2]), .valid_out(pv[i]));
        reg [31:0] acc;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) acc <= 32'd0;
            else if (av[i]) acc <= acc_q[32*i +: 32];
        end
        ot_hdc_fp32_add_lat #(.LAT(AL)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(pv[i]), .a(prod[32*i +: 32]), .b(acc),
            .y(acc_q[32*i +: 32]), .err(ae[2*i +: 2]), .valid_out(av[i]));
    end endgenerate
    // pairwise tree over the lanes' accumulators
    wire [NL*32-1:0] lv [0:LG];
    wire [NL-1:0] lvv [0:LG];
    assign lv[0] = acc_q;
    assign lvv[0] = av;
    generate for (l = 0; l < LG; l = l + 1) begin : g_lv
        for (i = 0; i < (NL >> (l + 1)); i = i + 1) begin : g_n
            wire [1:0] e;
            ot_hdc_fp32_add_lat #(.LAT(AL)) u_t (.clk(clk), .rst_n(rst_n), .valid_in(lvv[l][2*i]),
                .a(lv[l][32*(2*i) +: 32]), .b(lv[l][32*(2*i+1) +: 32]), .y(lv[l+1][32*i +: 32]), .err(e),
                .valid_out(lvv[l+1][i]));
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= lv[LG][31:0]; fault <= |pe | |ae; end
    end
endmodule

module ot_hdc_fp_ctx_s (input wire clk, rst_n, v, input wire [1:0] sel, input wire [255:0] xa, xb, xc,
                        output wire [31:0] y, output wire fault);
    ot_hdc_fp_ctx #(.AL(7), .ML(6), .NL(8)) u (.*);
endmodule
module ot_hdc_fp_ctx_s9 (input wire clk, rst_n, v, input wire [1:0] sel, input wire [255:0] xa, xb, xc,
                         output wire [31:0] y, output wire fault);
    ot_hdc_fp_ctx #(.AL(3), .ML(4), .NL(8)) u (.*);
endmodule
