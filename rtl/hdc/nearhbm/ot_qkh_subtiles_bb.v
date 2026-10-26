`timescale 1ns/1ps
// el1011-q-kvd-head: blackbox views of the hardened head sub-tiles (rtl/hdc/nearhbm/ot_qkh_subtiles.sv) for the head route.
(* blackbox *)
module ot_qkh_lane8 (
    input wire clk, input wire rst_n, input wire [3:0] c_in, input wire [63:0] row_in, input wire [15:0] e_in,
    input wire [11:0] lt_in, input wire [1:0] hid, input wire [1:0] bsel, input wire q_valid_in, input wire [5:0] q_beat_in,
    input wire [127:0] q_data_in, output wire [31:0] kp, output wire kpv, output wire [63:0] nb, output wire gf
);
endmodule
(* blackbox *)
module ot_qkh_ktree (
    input wire clk, input wire rst_n, input wire [511:0] kp_in, input wire kpv_in, input wire [15:0] gf_in,
    output wire [31:0] sc_d, output wire sc_f, output wire g_f
);
endmodule
