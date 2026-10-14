`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 serial domain: the stream unit's chunk8 reducer at N = 64 lanes (8 chunks, 3 tree levels, LV 6) with the
// multiplier / adder latencies as parameters, a slice of the N = 1,024 reducer for timing: every per-element path
// (square, the 7-op chunk chains, tree / time steps, the BF16 result rounding and address adds) is the same logic;
// what grows with N is the tap / result multiplexing and the fan-out of the shared tag.  The N = 1,024 top is
// ot_hdc_v41x_vec_red1024 (rtl/hdc/v41x/ot_hdc_v41x_w11_phys.sv).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vec_red64s #(
    parameter integer MLAT = 3,
    parameter integer ALAT = 3
) (
    input  wire clk, input wire rst_n, input wire v_in, input wire [2047:0] x_in, input wire [63:0] live_in,
    input  wire mx_in, sq_in, input wire [3:0] lt_in, input wire span_in, input wire [2:0] l_in,
    input  wire last_in, input wire [7:0] nres_in, input wire rnd_in, input wire [23:0] rbase_in,
    input  wire [4:0] rsh_in, input wire [8:0] meta_in,
    output wire [7:0] o_we, output wire [191:0] o_addr, output wire [255:0] o_data, output wire [8:0] o_meta,
    output wire o_ev, output wire busy, output wire fault
);
    ot_hdc_v41x_vec_red #(.N(64), .MW(9), .MLAT(MLAT), .ALAT(ALAT)) u (.*);
endmodule
