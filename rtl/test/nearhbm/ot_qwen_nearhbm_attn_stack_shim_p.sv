`timescale 1ns/1ps
// BENCH-ONLY shim: the name ot_qwen_nearhbm_attn_stack bound to the timing successor ot_qwen_nearhbm_attn_stack_p
// (rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv), used through rtl/test/nearhbm/hubp_swap.sh (NHB_SWAP=hub,stack) in place
// of the pinned parent stack source, so the parent's benches run unchanged around the successor.  Nothing shipped includes it.
module ot_qwen_nearhbm_attn_stack #(
    parameter integer HD = 128,
    parameter integer S = 0,
    parameter integer R = 1,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 32,
    parameter integer ZW = 4,
    parameter [31:0]  SCALE = 32'h3DB504F3
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [13:0]       T,
    input  wire              q_valid,
    input  wire [5:0]        q_beat,
    input  wire [511:0]      q_data,
    output wire [R-1:0]      req_valid,
    output wire [R-1:0]      req_v,
    output wire [R-1:0]      req_g,
    output wire [13*R-1:0]   req_t,
    input  wire [R-1:0]      rsp_valid,
    input  wire [HD*8*R-1:0] rsp_data,
    input  wire              mi_valid,
    input  wire              mi_g,
    input  wire [1:0]        mi_hh,
    input  wire [31:0]       mi_data,
    output wire              so_valid,
    output wire [1:0]        so_type,
    output wire              so_g,
    output wire [1:0]        so_hh,
    output wire [3:0]        so_k,
    output wire              so_any,
    output wire [31:0]       so_data,
    output wire              pv_valid,
    output wire              pv_g,
    output wire [5:0]        pv_beat,
    output wire [511:0]      pv_data,
    output wire [1:0]        pv_done,
    output wire              fault,
    output wire [15:0]       ev                // cycle markers for the bench
);
    ot_qwen_nearhbm_attn_stack_p #(.HD(HD), .S(S), .R(R), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .DQ(DQ), .ZW(ZW),
                                   .SCALE(SCALE)) u_p (
        .clk(clk), .rst_n(rst_n), .start(start), .T(T), .q_valid(q_valid), .q_beat(q_beat), .q_data(q_data), .req_valid(req_valid), .req_v(req_v), .req_g(req_g), .req_t(req_t), .rsp_valid(rsp_valid), .rsp_data(rsp_data), .mi_valid(mi_valid), .mi_g(mi_g), .mi_hh(mi_hh), .mi_data(mi_data), .so_valid(so_valid), .so_type(so_type), .so_g(so_g), .so_hh(so_hh), .so_k(so_k), .so_any(so_any), .so_data(so_data), .pv_valid(pv_valid), .pv_g(pv_g), .pv_beat(pv_beat), .pv_data(pv_data), .pv_done(pv_done), .fault(fault), .ev(ev));
endmodule
