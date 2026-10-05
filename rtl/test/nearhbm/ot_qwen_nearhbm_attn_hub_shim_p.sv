`timescale 1ns/1ps
// BENCH-ONLY shim: the name ot_qwen_nearhbm_attn_hub bound to the timing successor ot_qwen_nearhbm_attn_hub_p.  The
// successor's benches use it, through rtl/test/nearhbm/hubp_swap.sh, in place of the pinned parent hub source.  The
// parent's benches (rtl/test/nearhbm/*, rtl/test/qwen_sys/*) thereby run unchanged around the successor.  Nothing
// shipped includes this file.
module ot_qwen_nearhbm_attn_hub #(
    parameter integer HD = 128,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer ZW = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire [3:0]    si_valid,
    input  wire [7:0]    si_type,
    input  wire [3:0]    si_g,
    input  wire [7:0]    si_hh,
    input  wire [15:0]   si_k,
    input  wire [3:0]    si_any,
    input  wire [127:0]  si_data,
    input  wire [3:0]    pi_valid,
    input  wire [3:0]    pi_g,
    input  wire [23:0]   pi_beat,
    input  wire [2047:0] pi_data,
    output wire          mo_valid,
    output wire          mo_g,
    output wire [1:0]    mo_hh,
    output wire [31:0]   mo_data,
    output wire          out_valid,
    output wire          out_g,
    output wire [5:0]    out_beat,
    output wire [511:0]  out_data,
    output wire          fault,
    output wire [7:0]    ev
);
    ot_qwen_nearhbm_attn_hub_p #(.HD(HD), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .ZW(ZW)) u_p (
        .clk(clk), .rst_n(rst_n), .start(start), .si_valid(si_valid), .si_type(si_type), .si_g(si_g), .si_hh(si_hh),
        .si_k(si_k), .si_any(si_any), .si_data(si_data), .pi_valid(pi_valid), .pi_g(pi_g), .pi_beat(pi_beat),
        .pi_data(pi_data), .mo_valid(mo_valid), .mo_g(mo_g), .mo_hh(mo_hh), .mo_data(mo_data), .out_valid(out_valid),
        .out_g(out_g), .out_beat(out_beat), .out_data(out_data), .fault(fault), .ev(ev));
endmodule
