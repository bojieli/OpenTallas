`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_su_softmax_add: the add used at the softmax unit's register-to-register sites.  ADD6 = 0: the keep-prefix
// LAT-4/LAT-5 adder of the f12 lane build (ot_hdc_qadd_lat, rtl/hdc/ot_hdc_fastfp_lat_f12.sv).  ADD6 = 1: the
// six-cut f12 adder (ot_dsrom_su_softmax_add6, CUTS 7'b1101011, LAT 6), for operands that come out of another unit
// (the max hold, the row-sum tree, the denominator, the RoPE tail), the coordinator's rule after su_norm's in-context
// misses.  ADD6 = 2 (MARGIN build): ot_dsrom_su_softmax_add9, an input register + all seven cuts, LAT 9
// (rtl/hdc/v41x/ot_dsrom_su_softmax_m9.sv).  Same function, bit for bit; only the register boundary moves.
// ---------------------------------------------------------------------------
module ot_dsrom_su_softmax_add #(
    parameter integer ADD6 = 0,
    parameter integer LA   = 4
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    generate if (ADD6 == 2) begin : g_a9
        wire [1:0] err;
        wire       vo;
        ot_dsrom_su_softmax_add9 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                    .valid_out(vo));
        assign fault = vo && (err != 2'd0);
    end else if (ADD6) begin : g_a6
        wire [1:0] err;
        wire       vo;
        ot_dsrom_su_softmax_add6 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                    .valid_out(vo));
        assign fault = vo && (err != 2'd0);    // ot_hdc_qadd_lat's convention (a fault only on a valid result)
    end else begin : g_a
        ot_hdc_qadd_lat #(.KEEP(1), .LAT(LA)) u (.clk(clk), .rst_n(rst_n), .v(v), .a(a), .b(b), .y(y), .fault(fault));
    end endgenerate
endmodule
