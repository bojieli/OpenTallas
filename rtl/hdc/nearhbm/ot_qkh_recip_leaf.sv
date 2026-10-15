`timescale 1ns/1ps
// Hardened reciprocal boundary: pin registers add two cycles; core arithmetic
// and rounding match ot_qwen_nearhbm_recip_p. Local reset copies bound fanout.
module ot_qkh_recip_leaf (
 input wire clk, rst_n, v,
 input wire [31:0] x,
 output reg [31:0] y,
 output reg vo, fault
);
 wire [0:0] rr;
 ot_rst_relay #(.REGIONS(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
 reg [31:0] xq;
 reg vq;
 always @(posedge clk) xq <= x;
 always @(posedge clk or negedge rr[0])
   if (!rr[0]) vq <= 1'b0; else vq <= v;
 wire [31:0] cy;
 wire cv, cf;
 // kvsys-elements r2 2026-10-14 (native pin audit: rst_n capture 233.9 ps > 190): the core takes the local synchronised
 // reset like every other flop here; the raw pin no longer fans into the core's reset tree.
 ot_qkh_recip_core u_core (.clk(clk), .rst_n(rr[0]), .v(vq), .x(xq), .y(cy), .vo(cv), .fault(cf));
 always @(posedge clk) y <= cy;
 always @(posedge clk or negedge rr[0])
   if (!rr[0]) begin vo <= 1'b0; fault <= 1'b0; end
   else begin vo <= cv; fault <= cf; end
endmodule
module ot_qkh_recip_core #(
    parameter integer LA = 7,
    parameter integer LM = 7
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output wire [31:0] y,
    output wire        vo,
    output wire        fault
);
    wire [9:0] rr;
    ot_rst_relay #(.REGIONS(10)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    localparam integer IT = 2 * LM + LA;
    localparam integer DEPTH = 1 + 3 * IT;      // 64 at LA 7, LM 7
    wire [DEPTH:0] vd;
    ot_hdc_vline #(.D(DEPTH)) u_v (.clk(clk), .rst_n(rr[0]), .v(v), .vd(vd));
    assign vo = vd[DEPTH];

    reg [31:0] y0, d1;
    always @(posedge clk) begin
        // Keep the short pipeline bit-exact with the full pipeline when its
        // bit seed exceeds the supported finite-denominator range.
        y0 <= (!x[31] && x[30:23] != 8'hff && x > 32'h7EF311C7)
            ? 32'h00000000 : 32'h7EF311C7 - x;
        d1 <= x;
    end
    wire [31:0] yi [0:3];
    wire [31:0] dd [0:2];
    wire [31:0] m [0:2];
    wire [31:0] s [0:2];
    wire [31:0] yd [0:2];
    wire [8:0] f;
    assign yi[0] = y0;
    assign dd[0] = d1;
    genvar k;
    generate
        for (k = 0; k < 3; k = k + 1) begin : g_nr
            if (k < 2) begin : g_d
                ot_hdc_delay #(.W(32), .D(IT)) d_d (clk, rst_n, dd[k], dd[k+1]);
            end
            ot_qwen_nearhbm_qmul #(.LAT(LM)) m_m (clk, rr[1+3*k], vd[1 + IT*k], dd[k], yi[k], m[k], f[3*k]);
            ot_qwen_nearhbm_qadd #(.LAT(LA)) a_s (clk, rr[2+3*k], vd[1 + IT*k + LM], 32'h40000000, {~m[k][31], m[k][30:0]}, s[k], f[3*k+1]);
            ot_hdc_delay #(.W(32), .D(LM + LA)) d_y (clk, rst_n, yi[k], yd[k]);
            ot_qwen_nearhbm_qmul #(.LAT(LM)) m_y (clk, rr[3+3*k], vd[1 + IT*k + LM + LA], yd[k], s[k], yi[k+1], f[3*k+2]);
        end
    endgenerate
    assign y = yi[3];
    assign fault = |f;
endmodule
