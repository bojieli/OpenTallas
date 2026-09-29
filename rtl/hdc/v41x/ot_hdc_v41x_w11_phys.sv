`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 fixed-parameter tops for the ASAP7 hardening of the V4.1 dedicated units at the
// model's spec widths (tools/uarch_model.py DEDICATED; results/physical_abi3/asap7/hdc/v41x/w11/).
// Each is a plain instance so a route needs no -chparam.
//
//   ot_hdc_v41x_vec_red1024   the stream unit's ONE chunk8 reducer over N = 1,024 lanes
//                             (the unit is one controller + one reducer; the lane is the element)
// ---------------------------------------------------------------------------
module ot_hdc_v41x_vec_red1024 (
    input  wire clk, input wire rst_n, input wire v_in, input wire [32767:0] x_in, input wire [1023:0] live_in,
    input  wire mx_in, sq_in, input wire [3:0] lt_in, input wire span_in, input wire [2:0] l_in,
    input  wire last_in, input wire [7:0] nres_in, input wire rnd_in, input wire [23:0] rbase_in,
    input  wire [4:0] rsh_in, input wire [8:0] meta_in,
    output wire [127:0] o_we, output wire [3071:0] o_addr, output wire [4095:0] o_data, output wire [8:0] o_meta,
    output wire o_ev, output wire busy, output wire fault
);
    ot_hdc_v41x_vec_red #(.N(1024), .MW(9)) u (.*);
endmodule
