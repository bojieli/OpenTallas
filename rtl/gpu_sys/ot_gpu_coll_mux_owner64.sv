`timescale 1ns/1ps
// Item9 default-off structural successor: NL128 owner select slices 256 ->64 bits.
// No extra cycles, payload register, credit or arbitration change.
module ot_gpu_coll_mux_owner64 #(
    parameter integer ENABLE = 0,
    parameter integer NSM    = 2,
    parameter integer NL     = 128,
    parameter integer OWNER64 = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [NSM-1:0]        s_req_v,
    output wire [NSM-1:0]        s_req_rdy,
    input  wire [NSM-1:0]        s_mode,
    input  wire [NSM*8-1:0]      s_count,
    input  wire [NSM*NL*32-1:0]  s_data,
    output wire [NSM-1:0]        s_rsp_v,
    input  wire [NSM-1:0]        s_rsp_rdy,
    output wire [NL*32-1:0]      s_rsp_data,
    output wire                  m_req_v,
    input  wire                  m_req_rdy,
    output wire                  m_mode,
    output wire [7:0]            m_count,
    output wire [NL*32-1:0]      m_data,
    input  wire                  m_rsp_v,
    output wire                  m_rsp_rdy,
    input  wire [NL*32-1:0]      m_rsp_data
);
    // Off preserves the pinned f12 implementation; only owner-locality changes.
    ot_gpu_coll_mux_f12 #(.ENABLE(ENABLE), .NSM(NSM), .NL(NL),
        .ODUP(OWNER64 != 0 ? 64 : 16)) u_impl (
        .clk(clk), .rst_n(rst_n), .s_req_v(s_req_v), .s_req_rdy(s_req_rdy), .s_mode(s_mode), .s_count(s_count), .s_data(s_data), .s_rsp_v(s_rsp_v), .s_rsp_rdy(s_rsp_rdy), .s_rsp_data(s_rsp_data), .m_req_v(m_req_v), .m_req_rdy(m_req_rdy), .m_mode(m_mode), .m_count(m_count), .m_data(m_data), .m_rsp_v(m_rsp_v), .m_rsp_rdy(m_rsp_rdy), .m_rsp_data(m_rsp_data)
    );
endmodule
