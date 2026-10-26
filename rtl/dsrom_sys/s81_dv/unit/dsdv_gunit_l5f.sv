`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-GUNIT3 (2026-10-17): dsdv_gunit_l5f -- G-unit side leaf L5f (E of L5): the HC tail's exp (ot_dsrom_exp_f12,
// LM 5 / LA 4, depth 76) and reciprocal (ot_dsrom_fdiv_f12 1 / b, depth 21), split out of L5 (the one-leaf L5 was 23,268
// sinks on one root, TT insertion 563 ps / spread 109 ps: clock-rule FAIL).  Unchanged units, bit-identical results.
// W face only (L5): operands land in input flops, results / valids / faults leave from output flops (dsdv_gunit_tail's
// XS = 3 counts this leaf's 2 edges and L5's input flop).
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_gunit_l5f #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          xe_v, input wire [31:0] xe_x, output reg ye_v, output reg [31:0] ye_y, output reg ye_f,
    input  wire          xd_v, input wire [31:0] xd_b, output reg yd_v, output reg [31:0] yd_y, output reg yd_f
);
    localparam integer LM = 5, LA = 4;
    // reset relay (S81U-GUNIT4): the rst_n port drives only ot_rst_relay; 2 kept region copies (each <= ~256
    // reset loads, no port net spans the leaf).  Release is 3 edges after the port (transaction-level exact).
    wire [1:0] rq;
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rq));
    reg ev, dv; reg [31:0] ex, db;
    always @(posedge clk or negedge rq[0]) if (!rq[0]) begin ev <= 1'b0; dv <= 1'b0; end else begin ev <= xe_v; dv <= xd_v; end
    always @(posedge clk) begin ex <= xe_x; db <= xd_b; end
    wire [31:0] ey, dy; wire eo, ef, do_, df;
    ot_dsrom_exp_f12 #(.LM(LM), .LA(LA)) u_exp (.clk(clk), .rst_n(rq[0]), .v(ev), .x(ex), .y(ey), .vo(eo), .fault(ef));
    ot_dsrom_fdiv_f12 u_div (.clk(clk), .rst_n(rq[1]), .v(dv), .a(32'h3f800000), .b(db), .y(dy), .vo(do_), .fault(df));
    always @(posedge clk or negedge rq[1])
        if (!rq[1]) begin ye_v <= 1'b0; yd_v <= 1'b0; end else begin ye_v <= eo; yd_v <= do_; end
    always @(posedge clk) begin ye_y <= ey; ye_f <= ef; yd_y <= dy; yd_f <= df; end
endmodule
