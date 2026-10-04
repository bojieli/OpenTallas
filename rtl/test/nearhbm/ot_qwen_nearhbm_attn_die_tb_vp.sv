`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_qwen_nearhbm_attn_die_tb_vp: the verify-block bench top (successor of ot_qwen_nearhbm_attn_die_tb.sv, untouched).
// VP lane sets: VP copies of {4 stacks (ot_qwen_nearhbm_attn_stack_vp, VMASK) + hub + links}, one per verify position,
// each with its own q and mask context TM[i]; they share ONE HBM K/V stream: copy 0's requests go to the HBM and every
// response is broadcast to all copies.  The copies' request streams must be identical cycle by cycle (the stack's
// schedule depends only on T); any difference raises fault[5] (lockstep check).  VP = 1, VMASK = 0 is the parent.
// Bench top for the near-HBM attention exact gate: 4 stacks + the hub + the hub<->stack links (LINK register stages
// each way; 512-b data + a 32-b sideband).  The HBM itself (request queue, 750 B/cycle per stack token bucket,
// latency) is modelled by the C++ harness tb_qwen_nearhbm_attn.cpp.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_attn_die_tb_vp #(
    parameter integer VP = 2,
    parameter integer VMASK = 1,
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
    input  wire [VP*14-1:0]     TM,
    input  wire                 q_valid,
    input  wire [5:0]           q_beat,
    input  wire [VP*512-1:0]    q_data,
    output wire [4*R-1:0]       req_valid,
    output wire [4*R-1:0]       req_v,
    output wire [4*R-1:0]       req_g,
    output wire [4*13*R-1:0]    req_t,
    input  wire [4*R-1:0]       rsp_valid,
    input  wire [4*HD*8*R-1:0]  rsp_data,
    output wire [VP-1:0]        out_valid,
    output wire [VP-1:0]        out_g,
    output wire [VP*6-1:0]      out_beat,
    output wire [VP*512-1:0]    out_data,
    output wire [5:0]           fault,
    output wire [4*16-1:0]      ev_stack,
    output wire [7:0]           ev_hub
);
    wire [VP*4*R-1:0]    c_req_valid, c_req_v, c_req_g;
    wire [VP*4*13*R-1:0] c_req_t;
    wire [VP*5-1:0]      c_fault;
    wire [VP*4*16-1:0]   c_ev_stack;
    wire [VP*8-1:0]      c_ev_hub;
    assign req_valid = c_req_valid[4*R-1:0];
    assign req_v = c_req_v[4*R-1:0];
    assign req_g = c_req_g[4*R-1:0];
    assign req_t = c_req_t[4*13*R-1:0];
    assign ev_stack = c_ev_stack[4*16-1:0];
    assign ev_hub = c_ev_hub[7:0];
    reg [4:0] fault_or;
    reg       lockstep_bad;
    integer ci;
    always @* begin
        fault_or = 5'd0; lockstep_bad = 1'b0;
        for (ci = 0; ci < VP; ci = ci + 1) begin
            fault_or = fault_or | c_fault[5*ci +: 5];
            if (c_req_valid[4*R*ci +: 4*R] != c_req_valid[4*R-1:0]) lockstep_bad = 1'b1;
            if ((c_req_v[4*R*ci +: 4*R] & c_req_valid[4*R*ci +: 4*R]) != (c_req_v[4*R-1:0] & c_req_valid[4*R-1:0])) lockstep_bad = 1'b1;
            if ((c_req_g[4*R*ci +: 4*R] & c_req_valid[4*R*ci +: 4*R]) != (c_req_g[4*R-1:0] & c_req_valid[4*R-1:0])) lockstep_bad = 1'b1;
            if (c_req_t[4*13*R*ci +: 4*13*R] != c_req_t[4*13*R-1:0]) lockstep_bad = 1'b1;   // lockstep: even idle values agree
        end
    end
    reg lock_f;
    always @(posedge clk or negedge rst_n) if (!rst_n) lock_f <= 1'b0; else if (lockstep_bad) lock_f <= 1'b1;
    assign fault = {lock_f, fault_or};
    genvar cp;
    generate for (cp = 0; cp < VP; cp = cp + 1) begin : g_cp
    // q into every stack over its link
    wire        qv_l;
    wire [5:0]  qb_l;
    wire [511:0] qd_l;
    ot_hdc_delay #(.W(1), .D(LINK), .RESET(1)) u_qv (.clk(clk), .rst_n(rst_n), .d(q_valid), .q(qv_l));
    ot_hdc_delay #(.W(518), .D(LINK)) u_qd (.clk(clk), .rst_n(rst_n), .d({q_beat, q_data[512*cp +: 512]}), .q({qb_l, qd_l}));
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
    for (genvar s = 0; s < 4; s = s + 1) begin : g_s
        wire so_valid, so_g, so_any, pv_valid, pv_g, f;
        wire [1:0] so_type, so_hh, pv_done;
        wire [3:0] so_k;
        wire [31:0] so_data;
        wire [5:0] pv_beat;
        wire [511:0] pv_data;
        ot_qwen_nearhbm_attn_stack_vp #(.HD(HD), .S(s), .R(R), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT),
                                     .DQ(DQ), .ZW(ZW), .SCALE(SCALE), .VMASK(VMASK)) u_stack (
            .clk(clk), .rst_n(rst_n), .start(start), .T(T), .TM(TM[14*cp +: 14]), .q_valid(qv_l), .q_beat(qb_l), .q_data(qd_l),
            .req_valid(c_req_valid[4*R*cp + R*s +: R]), .req_v(c_req_v[4*R*cp + R*s +: R]), .req_g(c_req_g[4*R*cp + R*s +: R]),
            .req_t(c_req_t[4*13*R*cp + 13*R*s +: 13*R]), .rsp_valid(rsp_valid[R*s +: R]), .rsp_data(rsp_data[HD*8*R*s +: HD*8*R]),
            .mi_valid(mi_valid), .mi_g(mi_g), .mi_hh(mi_hh), .mi_data(mi_data), .so_valid(so_valid),
            .so_type(so_type), .so_g(so_g), .so_hh(so_hh), .so_k(so_k), .so_any(so_any), .so_data(so_data),
            .pv_valid(pv_valid), .pv_g(pv_g), .pv_beat(pv_beat), .pv_data(pv_data), .pv_done(pv_done), .fault(f),
            .ev(c_ev_stack[64*cp + 16*s +: 16]));
        assign c_fault[5*cp + s] = f;
        ot_hdc_delay #(.W(2), .D(LINK), .RESET(1)) u_sv (.clk(clk), .rst_n(rst_n), .d({so_valid, pv_valid}),
                                                         .q({si_valid[s], pi_valid[s]}));
        ot_hdc_delay #(.W(42 + 7 + 512), .D(LINK)) u_sd (.clk(clk), .rst_n(rst_n),
            .d({so_type, so_g, so_hh, so_k, so_any, so_data, pv_g, pv_beat, pv_data}),
            .q({si_type[2*s +: 2], si_g[s], si_hh[2*s +: 2], si_k[4*s +: 4], si_any[s], si_data[32*s +: 32],
                pi_g[s], pi_beat[6*s +: 6], pi_data[512*s +: 512]}));
    end
    ot_qwen_nearhbm_attn_hub #(.HD(HD), .ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .ZW(ZW)) u_hub (
        .clk(clk), .rst_n(rst_n), .start(start), .si_valid(si_valid), .si_type(si_type), .si_g(si_g), .si_hh(si_hh),
        .si_k(si_k), .si_any(si_any), .si_data(si_data), .pi_valid(pi_valid), .pi_g(pi_g), .pi_beat(pi_beat),
        .pi_data(pi_data), .mo_valid(mo_valid), .mo_g(mo_g), .mo_hh(mo_hh), .mo_data(mo_data),
        .out_valid(out_valid[cp]), .out_g(out_g[cp]), .out_beat(out_beat[6*cp +: 6]), .out_data(out_data[512*cp +: 512]),
        .fault(c_fault[5*cp + 4]), .ev(c_ev_hub[8*cp +: 8]));
    end endgenerate
endmodule
