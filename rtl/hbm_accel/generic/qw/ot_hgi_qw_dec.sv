`timescale 1ns/1ps
`default_nettype none
// ot_hgi_quant_wide_h decode tile (el1011-hbm-fq, 2026-10-11): ot_hgi_quant_decode hardened with registered seams (input
// flops on v / header / x, output flops on vo / y / faults; +2 edges).  generic_enable = 1 and legacy_fp4 = 0 by design
// (the wide fast path's only mode, as in ot_hgi_quant_wide).  Valids / faults reset, data free-running.
module ot_hgi_qw_dec (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [127:0]  header,
    input  wire [1023:0] x,
    output reg           vo,
    output reg  [511:0]  y,
    output reg           fault,
    output reg           decode_fault
);
    wire [1:0] rr_n;
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg i_v; reg [127:0] i_h; reg [1023:0] i_x;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) i_v <= 0; else i_v <= v;
    always @(posedge clk) begin i_h <= header; i_x <= x; end
    wire d_vo, d_f, d_df; wire [511:0] d_y;
    ot_hgi_quant_decode u_dec (.clk(clk), .rst_n(rr_n[1]), .v(i_v), .generic_enable(1'b1), .legacy_fp4(1'b0),
        .header(i_h), .x(i_x), .vo(d_vo), .y(d_y), .fault(d_f), .decode_fault(d_df));
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin vo <= 0; fault <= 0; decode_fault <= 0; end
        else begin vo <= d_vo; fault <= d_f; decode_fault <= d_df; end
    always @(posedge clk) y <= d_y;
endmodule
`default_nettype wire
