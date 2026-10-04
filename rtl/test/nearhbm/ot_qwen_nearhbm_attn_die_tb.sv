`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Bench top for the near-HBM attention exact gate: 4 stacks + the hub + the hub<->stack links (LINK register stages
// each way; 512-b data + a 32-b sideband).  The HBM itself (request queue, 750 B/cycle per stack token bucket,
// latency) is modelled by the C++ harness tb_qwen_nearhbm_attn.cpp.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_attn_die_tb #(
    parameter integer HD = 128,
    parameter integer R = 1,
    parameter integer LINK = 45,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 32,
    parameter integer ZW = 4,
    parameter [31:0]  SCALE = 32'h3DB504F3
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,
    input  wire [13:0]          T,
    input  wire                 q_valid,
    input  wire [5:0]           q_beat,
    input  wire [511:0]         q_data,
    output wire [4*R-1:0]       req_valid,
    output wire [4*R-1:0]       req_v,
    output wire [4*R-1:0]       req_g,
    output wire [4*13*R-1:0]    req_t,
    input  wire [4*R-1:0]       rsp_valid,
    input  wire [4*HD*8*R-1:0]  rsp_data,
    output wire                 out_valid,
    output wire                 out_g,
    output wire [5:0]           out_beat,
    output wire [511:0]         out_data,
    output wire [4:0]           fault,
    output wire [4*16-1:0]      ev_stack,
    output wire [7:0]           ev_hub
);
    // q into every stack over its link
    wire        qv_l;
    wire [5:0]  qb_l;
    wire [511:0] qd_l;
    ot_hdc_delay #(.W(1), .D(LINK), .RESET(1)) u_qv (.clk(clk), .rst_n(rst_n), .d(q_valid), .q(qv_l));
    ot_hdc_delay #(.W(518), .D(LINK)) u_qd (.clk(clk), .rst_n(rst_n), .d({q_beat, q_data}), .q({qb_l, qd_l}));
    // M from the hub over the links
    wire        mo_valid, mo_g;
    wire [1:0]  mo_hh;
    wire [31:0] mo_data;
    wire        mi_valid, mi_g;
    wire [1:0]  mi_hh;
    wire [31:0] mi_data;
    ot_hdc_delay #(.W(1), .D(LINK), .RESET(1)) u_mv (.clk(clk), .rst_n(rst_n), .d(mo_valid), .q(mi_valid));
    ot_hdc_delay #(.W(35), .D(LINK)) u_md (.clk(clk), .rst_n(rst_n), .d({mo_g, mo_hh, mo_data}),
                                           .q({mi_g, mi_hh, mi_data}));
    // stacks
    wire [3:0]    si_valid, si_g, si_any, pi_valid, pi_g;
    wire [7:0]    si_type, si_hh;
    wire [15:0]   si_k;
    wire [127:0]  si_data;
    wire [23:0]   pi_beat;
    wire [2047:0] pi_data;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_s
        wire so_valid, so_g, so_any, pv_valid, pv_g, f;
        wire [1:0] so_type, so_hh, pv_done;
        wire [3:0] so_k;
        wire [31:0] so_data;
        wire [5:0] pv_beat;
        wire [511:0] pv_data;
        ot_qwen_nearhbm_attn_stack #(.HD(HD), .S(s), .R(R), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT),
                                     .DQ(DQ), .ZW(ZW), .SCALE(SCALE)) u_stack (
            .clk(clk), .rst_n(rst_n), .start(start), .T(T), .q_valid(qv_l), .q_beat(qb_l), .q_data(qd_l),
            .req_valid(req_valid[R*s +: R]), .req_v(req_v[R*s +: R]), .req_g(req_g[R*s +: R]),
            .req_t(req_t[13*R*s +: 13*R]), .rsp_valid(rsp_valid[R*s +: R]), .rsp_data(rsp_data[HD*8*R*s +: HD*8*R]),
            .mi_valid(mi_valid), .mi_g(mi_g), .mi_hh(mi_hh), .mi_data(mi_data), .so_valid(so_valid),
            .so_type(so_type), .so_g(so_g), .so_hh(so_hh), .so_k(so_k), .so_any(so_any), .so_data(so_data),
            .pv_valid(pv_valid), .pv_g(pv_g), .pv_beat(pv_beat), .pv_data(pv_data), .pv_done(pv_done), .fault(f),
            .ev(ev_stack[16*s +: 16]));
        assign fault[s] = f;
        ot_hdc_delay #(.W(2), .D(LINK), .RESET(1)) u_sv (.clk(clk), .rst_n(rst_n), .d({so_valid, pv_valid}),
                                                         .q({si_valid[s], pi_valid[s]}));
        ot_hdc_delay #(.W(42 + 7 + 512), .D(LINK)) u_sd (.clk(clk), .rst_n(rst_n),
            .d({so_type, so_g, so_hh, so_k, so_any, so_data, pv_g, pv_beat, pv_data}),
            .q({si_type[2*s +: 2], si_g[s], si_hh[2*s +: 2], si_k[4*s +: 4], si_any[s], si_data[32*s +: 32],
                pi_g[s], pi_beat[6*s +: 6], pi_data[512*s +: 512]}));
    end endgenerate
    ot_qwen_nearhbm_attn_hub #(.HD(HD), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .ZW(ZW)) u_hub (
        .clk(clk), .rst_n(rst_n), .start(start), .si_valid(si_valid), .si_type(si_type), .si_g(si_g), .si_hh(si_hh),
        .si_k(si_k), .si_any(si_any), .si_data(si_data), .pi_valid(pi_valid), .pi_g(pi_g), .pi_beat(pi_beat),
        .pi_data(pi_data), .mo_valid(mo_valid), .mo_g(mo_g), .mo_hh(mo_hh), .mo_data(mo_data),
        .out_valid(out_valid), .out_g(out_g), .out_beat(out_beat), .out_data(out_data), .fault(fault[4]),
        .ev(ev_hub));
endmodule
