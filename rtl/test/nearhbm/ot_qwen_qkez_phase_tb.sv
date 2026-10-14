`timescale 1ns/1ps
// Test instrumentation only: observes the actual stack/hub phase pipelines.
module ot_qwen_qkez_phase_tb #(
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
    output wire [4*R-1:0] dbg_sc_v, dbg_ew_v,
    output wire [48*R-1:0] dbg_sc_a, dbg_ew_a,
    output wire [512*R-1:0] dbg_sc_d,
    output wire [256*R-1:0] dbg_ew_d,
    output wire dbg_m_v, dbg_m_g, dbg_z_v,
    output wire [1:0] dbg_m_h,
    output wire [2:0] dbg_z_h,
    output wire [31:0] dbg_m_d, dbg_z_d,
    output wire [7:0]           ev_hub
);
    ot_qwen_nearhbm_attn_die_tb #(.HD(HD),.R(R),.LINK(LINK),.ADD_LAT(ADD_LAT),.MUL_LAT(MUL_LAT),.DQ(DQ),.ZW(ZW),.SCALE(SCALE)) u_attn (.*);
    genvar s;
    generate for(s=0;s<4;s=s+1) begin : g_debug
        assign dbg_sc_v[R*s +: R] = u_attn.g_s[s].u_stack.u_p.sc_valid;
        assign dbg_sc_a[12*R*s +: 12*R] = u_attn.g_s[s].u_stack.u_p.sc_addr;
        assign dbg_sc_d[128*R*s +: 128*R] = u_attn.g_s[s].u_stack.u_p.sc_data;
        assign dbg_ew_v[R*s +: R] = u_attn.g_s[s].u_stack.u_p.ew_valid;
        assign dbg_ew_a[12*R*s +: 12*R] = u_attn.g_s[s].u_stack.u_p.ew_addr;
        assign dbg_ew_d[64*R*s +: 64*R] = u_attn.g_s[s].u_stack.u_p.ew_data;
    end endgenerate
    assign dbg_m_v=u_attn.mo_valid;
    assign dbg_m_g=u_attn.mo_g;
    assign dbg_m_h=u_attn.mo_hh;
    assign dbg_m_d=u_attn.mo_data;
    assign dbg_z_v=u_attn.u_hub.u_p.rv1;
    assign dbg_z_d=u_attn.u_hub.u_p.rx;
    reg [2:0] zh;
    // rx and rv1 both capture ra0/rv0 on this edge; keep the same tag latency.
    always @(posedge clk) zh <= u_attn.u_hub.u_p.ra0;
    assign dbg_z_h=zh;
endmodule
